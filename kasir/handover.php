<?php
/**
 * FILE: kasir/handover.php
 * FUNGSI: Serahkan uang ke admin - PER PICKUP FAST ACTION
 * VERSION: 4.0 - Per Pickup, Tombol Aksi Langsung
 */

require_once '../config.php';
require_once '../telegram-config.php';
check_login();
check_role('kasir');

$success = '';
$error = '';
$user_id = $_SESSION['user_id'];

// Proses penyerahan (1 pickup)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['pickup_id'])) {
    $pickup_id = intval($_POST['pickup_id']);
    $handover_date = date('Y-m-d H:i:s');
    $notes = clean_input($_POST['notes'] ?? '');

    // Ambil data pickup
    $query_pickup = "SELECT p.*, o.outlet_name
                     FROM pickups p
                     JOIN outlets o ON p.outlet_id = o.id
                     WHERE p.id = $pickup_id AND p.status = 'pending_handover'";
    $result_pickup = $conn->query($query_pickup);

    if ($result_pickup && $result_pickup->num_rows > 0) {
        $pickup = $result_pickup->fetch_assoc();
        $total_amount = $pickup['amount_taken'];
        $outlet_name = $pickup['outlet_name'];

        $conn->begin_transaction();

        try {
            // FIX: Insert tanpa 'recorded_by' (kolom tidak ada di tabel handovers)
            $pickup_ids_json = json_encode([$pickup_id]);
            $stmt = $conn->prepare("INSERT INTO handovers (handover_date, pickup_ids, total_amount, notes, status, created_at) VALUES (?, ?, ?, ?, 'pending_validation', NOW())");
            $stmt->bind_param("ssds", $handover_date, $pickup_ids_json, $total_amount, $notes);

            if (!$stmt->execute()) throw new Exception($stmt->error);

            $handover_id = $stmt->insert_id;
            $stmt->close();

            // Update status pickup
            $conn->query("UPDATE pickups SET status = 'handed_over', updated_at = NOW() WHERE id = $pickup_id");

            $conn->commit();

            // FIXED: Kirim notifikasi Telegram menggunakan fungsi & konstanta yang sudah ada
            $telegram_message = "🤝 <b>SETORAN KASIR BARU</b>\n\n";
            $telegram_message .= "🏪 Outlet: <b>" . $outlet_name . "</b>\n";
            $telegram_message .= "💰 Total: <b>Rp " . number_format($total_amount, 0, ',', '.') . "</b>\n";
            $telegram_message .= "👤 Kasir: " . $_SESSION['full_name'] . "\n";
            if ($notes) {
                $telegram_message .= "💬 Catatan: " . $notes . "\n";
            }
            $telegram_message .= "\n⏳ Menunggu validasi admin";

            $telegram_sent = sendTelegramNotification($telegram_message, TELEGRAM_CHAT_ID_KEUANGAN);

            $success = "✅ Berhasil menyerahkan pickup dari <strong>$outlet_name</strong> sebesar " . format_rupiah($total_amount) . "!";
            if (!$telegram_sent || !$telegram_sent['ok']) {
                $success .= " <small>(Notifikasi telegram gagal dikirim)</small>";
            }

        } catch (Exception $e) {
            $conn->rollback();
            $error = "Gagal menyimpan: " . $e->getMessage();
        }
    } else {
        $error = "Pickup tidak ditemukan atau sudah diserahkan!";
    }
}

// Get pickup yang belum diserahkan
$query_pending = "SELECT p.*, o.outlet_name, o.id as outlet_id
                  FROM pickups p
                  JOIN outlets o ON p.outlet_id = o.id
                  WHERE p.status = 'pending_handover'
                  ORDER BY p.pickup_date DESC, o.outlet_name ASC";
$result_pending = $conn->query($query_pending);

$total_pending = $conn->query("SELECT COUNT(*) as c, COALESCE(SUM(amount_taken), 0) as t FROM pickups WHERE status = 'pending_handover'")->fetch_assoc();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Serahkan ke Admin - LondriPedia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; }

        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header-content { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 20px; }
        .back-btn { background: rgba(255,255,255,0.2); color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; }

        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

        .alert { padding: 12px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
        .alert-success { background: #d1fae5; color: #065f46; border: 1px solid #10b981; }
        .alert-error { background: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }
        .alert-info { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }

        .summary-box { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .summary-box h3 { font-size: 16px; color: #666; margin-bottom: 15px; }
        .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .summary-item { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }
        .summary-item .label { font-size: 13px; color: #666; margin-bottom: 5px; }
        .summary-item .value { font-size: 24px; font-weight: bold; color: #667eea; }

        .section { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #333; }

        table { width: 100%; border-collapse: collapse; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-size: 13px; color: #666; font-weight: 600; border-bottom: 2px solid #e5e7eb; }
        td { padding: 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; vertical-align: middle; }

        .outlet-badge { display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .badge-monyonyo { background: #dbeafe; color: #1e40af; }
        .badge-londripedia { background: #d1fae5; color: #065f46; }

        .info-compact { font-size: 13px; line-height: 1.6; }
        .info-compact div { margin-bottom: 4px; }
        .info-compact .label { color: #666; display: inline-block; min-width: 70px; }
        .info-compact .value { color: #333; font-weight: 500; }

        .btn-action { padding: 8px 20px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; text-decoration: none; display: inline-block; }
        .btn-serahkan { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; }
        .btn-serahkan:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); }

        .empty-state { text-align: center; padding: 60px 20px; color: #999; }
        .empty-state .icon { font-size: 64px; margin-bottom: 15px; }
        .empty-state .text { font-size: 16px; }

        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal.show { display: flex; align-items: center; justify-content: center; }
        .modal-content { background: white; border-radius: 16px; padding: 30px; max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto; }
        .modal-header { margin-bottom: 20px; }
        .modal-header h3 { font-size: 20px; color: #333; }
        .modal-body { margin-bottom: 25px; }
        .modal-body .pickup-info { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; line-height: 1.8; }
        .modal-body .pickup-info strong { color: #667eea; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 14px; font-weight: 600; color: #333; margin-bottom: 8px; }
        .form-group textarea { width: 100%; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; font-family: inherit; resize: vertical; min-height: 100px; }
        .modal-footer { display: flex; gap: 10px; justify-content: flex-end; }
        .btn-cancel { background: #e5e7eb; color: #333; }
        .btn-cancel:hover { background: #d1d5db; }
        .btn-submit { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; }

        @media (max-width: 768px) {
            .container { padding: 15px; }
            .summary-grid { grid-template-columns: 1fr; }
            table { font-size: 12px; }
            th, td { padding: 8px; }
            .btn-action { padding: 6px 12px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div>
                <h1>📦 Serahkan ke Admin</h1>
            </div>
            <a href="dashboard.php" class="back-btn">← Kembali</a>
        </div>
    </div>

    <div class="container">
        <?php if ($success): ?>
            <div class="alert alert-success"><?php echo $success; ?></div>
        <?php endif; ?>

        <?php if ($error): ?>
            <div class="alert alert-error">❌ <?php echo $error; ?></div>
        <?php endif; ?>

        <!-- RINGKASAN -->
        <div class="summary-box">
            <h3>📊 Ringkasan</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Belum Disetor</div>
                    <div class="value"><?php echo $total_pending['c']; ?></div>
                </div>
                <div class="summary-item">
                    <div class="label">Total Uang</div>
                    <div class="value"><?php echo format_rupiah($total_pending['t']); ?></div>
                </div>
            </div>
        </div>

        <?php if ($total_pending['c'] == 0): ?>
            <div class="alert alert-info">
                ℹ️ <strong>Perhatian:</strong> Serahkan per outlet. Tidak boleh mencampur outlet dalam 1 setoran.
            </div>
        <?php endif; ?>

        <!-- DAFTAR PICKUP -->
        <div class="section">
            <div class="section-title">💰 Daftar Pickup Belum Disetor</div>

            <?php if ($result_pending->num_rows > 0): ?>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Outlet</th>
                                <th>Tanggal Pickup</th>
                                <th style="text-align: right;">Jumlah</th>
                                <th style="text-align: center; width: 120px;">Aksi</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php while ($row = $result_pending->fetch_assoc()): ?>
                                <?php
                                $outlet_class = (stripos($row['outlet_name'], 'monyonyo') !== false) ? 'badge-monyonyo' : 'badge-londripedia';
                                ?>
                                <tr>
                                    <td>
                                        <span class="outlet-badge <?php echo $outlet_class; ?>">
                                            <?php echo $row['outlet_name']; ?>
                                        </span>
                                    </td>
                                    <td>
                                        <div>
                                            <div style="font-size: 14px; color: #333;">
                                                📅 <?php echo date('d/m/Y H:i', strtotime($row['pickup_date'])); ?>
                                            </div>
                                        </div>
                                    </td>
                                    <td style="text-align: right;">
                                        <strong style="color: #10b981; font-size: 16px;">
                                            💰 <?php echo format_rupiah($row['amount_taken']); ?>
                                        </strong>
                                    </td>
                                    <td style="text-align: center;">
                                        <button class="btn-action btn-serahkan"
                                                onclick="showHandoverModal(<?php echo $row['id']; ?>, '<?php echo addslashes($row['outlet_name']); ?>', '<?php echo date('d/m/Y H:i', strtotime($row['pickup_date'])); ?>', <?php echo $row['amount_taken']; ?>)">
                                            ✓ Serahkan
                                        </button>
                                    </td>
                                </tr>
                            <?php endwhile; ?>
                        </tbody>
                    </table>
                </div>
            <?php else: ?>
                <div class="empty-state">
                    <div class="icon">📭</div>
                    <div class="text">Tidak ada pickup yang perlu diserahkan</div>
                </div>
            <?php endif; ?>
        </div>
    </div>

    <!-- MODAL SERAHKAN -->
    <div id="handoverModal" class="modal">
        <div class="modal-content">
            <form method="POST" id="handoverForm">
                <div class="modal-header">
                    <h3>✅ Konfirmasi Serahkan</h3>
                </div>

                <div class="modal-body">
                    <div class="pickup-info" id="pickupInfo"></div>

                    <div class="form-group">
                        <label>💬 Catatan (Opsional)</label>
                        <textarea name="notes" placeholder="Tulis catatan jika ada (misal: ada uang rusak, dll)"></textarea>
                    </div>

                    <input type="hidden" name="pickup_id" id="pickup_id">
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn-action btn-cancel" onclick="closeModal()">Batal</button>
                    <button type="submit" class="btn-action btn-submit">✓ Ya, Serahkan</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        const modal = document.getElementById('handoverModal');
        const form = document.getElementById('handoverForm');

        function showHandoverModal(id, outlet, tanggal, amount) {
            document.getElementById('pickup_id').value = id;
            document.getElementById('pickupInfo').innerHTML = `
                <div><strong>🏪 Outlet:</strong> ${outlet}</div>
                <div><strong>📅 Tanggal:</strong> ${tanggal}</div>
                <div><strong>💰 Jumlah:</strong> Rp ${amount.toLocaleString('id-ID')}</div>
            `;
            modal.classList.add('show');
        }

        function closeModal() {
            modal.classList.remove('show');
            form.reset();
        }

        // Close modal saat klik di luar
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Konfirmasi sebelum submit
        form.addEventListener('submit', function(e) {
            if (!confirm('Apakah Anda yakin ingin menyerahkan pickup ini ke admin?')) {
                e.preventDefault();
            }
        });
    </script>
</body>
</html>
