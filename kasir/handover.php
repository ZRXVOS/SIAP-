<?php
/**
 * FILE: kasir/handover.php
 * FUNGSI: Serahkan uang ke admin - MULTIPLE PICKUP SELECTION
 * VERSION: 5.0 - Compact Table dengan Pilih Multiple
 */

require_once '../config.php';
require_once '../telegram-config.php';
check_login();
check_role('kasir');

$success = '';
$error = '';
$user_id = $_SESSION['user_id'];

// Proses penyerahan (MULTIPLE PICKUPS)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['pickup_ids'])) {
    $pickup_ids = $_POST['pickup_ids'] ?? [];
    $handover_date = date('Y-m-d H:i:s');
    $notes = clean_input($_POST['notes'] ?? '');

    if (empty($pickup_ids) || !is_array($pickup_ids)) {
        $error = "Silakan pilih minimal 1 pickup untuk diserahkan!";
    } else {
        // Sanitize pickup IDs
        $pickup_ids = array_map('intval', $pickup_ids);
        $pickup_ids_str = implode(',', $pickup_ids);

        // Ambil data pickups yang dipilih
        $query_pickups = "SELECT p.*, o.outlet_name
                         FROM pickups p
                         JOIN outlets o ON p.outlet_id = o.id
                         WHERE p.id IN ($pickup_ids_str) AND p.status = 'pending_handover'";
        $result_pickups = $conn->query($query_pickups);

        if ($result_pickups && $result_pickups->num_rows > 0) {
            $total_amount = 0;
            $outlet_names = [];

            while ($pickup = $result_pickups->fetch_assoc()) {
                $total_amount += $pickup['amount_taken'];
                $outlet_names[$pickup['outlet_name']] = true;
            }

            $conn->begin_transaction();

            try {
                // Insert handover
                $pickup_ids_json = json_encode($pickup_ids);
                $stmt = $conn->prepare("INSERT INTO handovers (handover_date, pickup_ids, total_amount, notes, status, created_at) VALUES (?, ?, ?, ?, 'pending_validation', NOW())");
                $stmt->bind_param("ssds", $handover_date, $pickup_ids_json, $total_amount, $notes);

                if (!$stmt->execute()) throw new Exception($stmt->error);

                $handover_id = $stmt->insert_id;
                $stmt->close();

                // Update status semua pickups
                $conn->query("UPDATE pickups SET status = 'handed_over', updated_at = NOW() WHERE id IN ($pickup_ids_str)");

                $conn->commit();

                // Kirim notifikasi Telegram
                $outlet_list = implode(', ', array_keys($outlet_names));
                $telegram_message = "🤝 <b>SETORAN KASIR BARU</b>\n\n";
                $telegram_message .= "🏪 Outlet: <b>" . $outlet_list . "</b>\n";
                $telegram_message .= "📦 Jumlah Pickup: <b>" . count($pickup_ids) . "</b>\n";
                $telegram_message .= "💰 Total: <b>Rp " . number_format($total_amount, 0, ',', '.') . "</b>\n";
                $telegram_message .= "👤 Kasir: " . $_SESSION['full_name'] . "\n";
                if ($notes) {
                    $telegram_message .= "💬 Catatan: " . $notes . "\n";
                }
                $telegram_message .= "\n⏳ Menunggu validasi admin";

                $telegram_sent = sendTelegramNotification($telegram_message, TELEGRAM_CHAT_ID_KEUANGAN);

                $success = "✅ Berhasil menyerahkan " . count($pickup_ids) . " pickup sebesar " . format_rupiah($total_amount) . "!";
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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; padding-bottom: 40px; }

        /* HEADER */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.15);
            border-bottom: 3px solid #5a67d8;
        }
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 20px;
            font-weight: 600;
        }
        .back-btn {
            background: rgba(255,255,255,0.25);
            color: white;
            padding: 8px 18px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .back-btn:hover {
            background: rgba(255,255,255,0.35);
            transform: translateX(-2px);
        }

        .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }

        /* ALERTS */
        .alert {
            padding: 14px 18px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border-left: 4px solid #10b981;
        }
        .alert-error {
            background: #fee2e2;
            color: #991b1b;
            border-left: 4px solid #ef4444;
        }

        /* SUMMARY TOP */
        .summary-top {
            background: white;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #e5e7eb;
        }
        .summary-top .info {
            font-size: 15px;
            font-weight: 600;
            color: #333;
        }
        .summary-top .info span {
            color: #667eea;
            font-size: 16px;
        }
        .summary-top .select-all-btn {
            background: #f3f4f6;
            border: 2px solid #d1d5db;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .summary-top .select-all-btn:hover {
            background: #e5e7eb;
            border-color: #9ca3af;
        }

        /* TABLE COMPACT */
        .table-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
            border: 2px solid #e5e7eb;
        }
        .table-compact {
            width: 100%;
            border-collapse: collapse;
        }
        .table-compact thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .table-compact thead th {
            padding: 14px 16px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .table-compact thead th:first-child {
            width: 50px;
            text-align: center;
        }
        .table-compact tbody tr {
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.2s;
        }
        .table-compact tbody tr:hover {
            background: #f9fafb;
        }
        .table-compact tbody tr.selected {
            background: #eff6ff;
        }
        .table-compact tbody td {
            padding: 16px;
            font-size: 14px;
            color: #333;
        }
        .table-compact tbody td:first-child {
            text-align: center;
        }

        /* CHECKBOX CUSTOM */
        .checkbox-custom {
            width: 22px;
            height: 22px;
            cursor: pointer;
            accent-color: #667eea;
        }

        /* OUTLET BADGE */
        .outlet-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }
        .badge-monyonyo {
            background: #dbeafe;
            color: #1e40af;
        }
        .badge-londripedia {
            background: #d1fae5;
            color: #065f46;
        }

        /* AMOUNT */
        .amount {
            font-size: 15px;
            font-weight: 700;
            color: #10b981;
        }

        /* SUMMARY BOTTOM */
        .summary-bottom {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-top: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #e5e7eb;
        }
        .selected-info {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            padding: 16px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 15px;
            font-weight: 600;
            color: #1e40af;
            border: 2px solid #93c5fd;
        }
        .selected-info span {
            font-size: 18px;
            color: #667eea;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        .form-group textarea {
            width: 100%;
            padding: 14px;
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            min-height: 90px;
            transition: border 0.2s;
        }
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        /* SUBMIT BUTTON */
        .submit-container {
            text-align: center;
        }
        .btn-submit {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 16px 48px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        .btn-submit:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }
        .btn-submit:disabled {
            background: #d1d5db;
            cursor: not-allowed;
            box-shadow: none;
        }

        /* EMPTY STATE */
        .empty-state {
            text-align: center;
            padding: 80px 20px;
            color: #999;
        }
        .empty-state .icon {
            font-size: 80px;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        .empty-state .text {
            font-size: 18px;
            font-weight: 500;
        }

        /* RESPONSIVE */
        @media (max-width: 768px) {
            .container { padding: 0 15px; }
            .summary-top { flex-direction: column; gap: 12px; align-items: stretch; }
            .summary-top .select-all-btn { justify-content: center; }
            .table-compact thead th { padding: 10px 8px; font-size: 11px; }
            .table-compact tbody td { padding: 12px 8px; font-size: 13px; }
            .outlet-badge { font-size: 11px; padding: 4px 10px; }
            .amount { font-size: 13px; }
            .btn-submit { padding: 14px 36px; font-size: 15px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>💵 Serahkan ke Admin</h1>
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

        <?php if ($result_pending->num_rows > 0): ?>
            <form method="POST" id="handoverForm">
                <!-- SUMMARY TOP -->
                <div class="summary-top">
                    <div class="info">
                        Belum disetor: <span id="totalPickups"><?php echo $total_pending['c']; ?> pickup</span> •
                        Total: <span id="totalAmount">Rp <?php echo number_format($total_pending['t'], 0, ',', '.'); ?></span>
                    </div>
                    <button type="button" class="select-all-btn" onclick="toggleSelectAll()">
                        <input type="checkbox" id="selectAllCheckbox" class="checkbox-custom" onchange="toggleSelectAll()">
                        <span>Pilih Semua</span>
                    </button>
                </div>

                <!-- TABLE COMPACT -->
                <div class="table-container">
                    <table class="table-compact">
                        <thead>
                            <tr>
                                <th></th>
                                <th>OUTLET</th>
                                <th>PERIODE</th>
                                <th>TGL AMBIL</th>
                                <th style="text-align: right;">JUMLAH</th>
                                <th>CATATAN</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php while ($row = $result_pending->fetch_assoc()): ?>
                                <?php
                                $outlet_class = (stripos($row['outlet_name'], 'monyonyo') !== false) ? 'badge-monyonyo' : 'badge-londripedia';
                                ?>
                                <tr class="pickup-row" data-amount="<?php echo $row['amount_taken']; ?>">
                                    <td>
                                        <input type="checkbox"
                                               name="pickup_ids[]"
                                               value="<?php echo $row['id']; ?>"
                                               class="checkbox-custom pickup-checkbox"
                                               onchange="updateSummary()">
                                    </td>
                                    <td>
                                        <span class="outlet-badge <?php echo $outlet_class; ?>">
                                            <?php echo $row['outlet_name']; ?>
                                        </span>
                                    </td>
                                    <td>
                                        📅 <?php echo date('d/m/y', strtotime($row['pickup_date'])); ?>
                                    </td>
                                    <td>
                                        ✋ <?php echo date('d/m/y', strtotime($row['pickup_date'])); ?>
                                    </td>
                                    <td style="text-align: right;">
                                        <span class="amount">
                                            💰 Rp <?php echo number_format($row['amount_taken'], 0, ',', '.'); ?>
                                        </span>
                                    </td>
                                    <td>
                                        <?php echo $row['notes'] ? '💬' : ''; ?>
                                    </td>
                                </tr>
                            <?php endwhile; ?>
                        </tbody>
                    </table>
                </div>

                <!-- SUMMARY BOTTOM -->
                <div class="summary-bottom">
                    <div class="selected-info">
                        Dipilih: <span id="selectedCount">0 pickup</span> •
                        Total: <span id="selectedTotal">Rp 0</span>
                    </div>

                    <div class="form-group">
                        <label>💬 Catatan (opsional):</label>
                        <textarea name="notes" placeholder="Tulis catatan jika ada (misal: ada uang rusak, uang kembalian, dll)"></textarea>
                    </div>

                    <div class="submit-container">
                        <button type="submit" class="btn-submit" id="submitBtn" disabled>
                            💵 Serahkan ke Admin
                        </button>
                    </div>
                </div>
            </form>
        <?php else: ?>
            <div class="table-container">
                <div class="empty-state">
                    <div class="icon">📭</div>
                    <div class="text">Tidak ada pickup yang perlu diserahkan</div>
                </div>
            </div>
        <?php endif; ?>
    </div>

    <script>
        function updateSummary() {
            const checkboxes = document.querySelectorAll('.pickup-checkbox:checked');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const submitBtn = document.getElementById('submitBtn');
            const selectedCount = document.getElementById('selectedCount');
            const selectedTotal = document.getElementById('selectedTotal');

            let count = 0;
            let total = 0;

            checkboxes.forEach(checkbox => {
                count++;
                const row = checkbox.closest('tr');
                const amount = parseInt(row.dataset.amount);
                total += amount;
                row.classList.add('selected');
            });

            // Remove selected class from unchecked rows
            document.querySelectorAll('.pickup-checkbox:not(:checked)').forEach(checkbox => {
                checkbox.closest('tr').classList.remove('selected');
            });

            // Update summary
            selectedCount.textContent = count + ' pickup';
            selectedTotal.textContent = 'Rp ' + total.toLocaleString('id-ID');

            // Enable/disable submit button
            submitBtn.disabled = count === 0;

            // Update select all checkbox
            const allCheckboxes = document.querySelectorAll('.pickup-checkbox');
            selectAllCheckbox.checked = count === allCheckboxes.length && count > 0;
        }

        function toggleSelectAll() {
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const checkboxes = document.querySelectorAll('.pickup-checkbox');

            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });

            updateSummary();
        }

        // Konfirmasi sebelum submit
        document.getElementById('handoverForm').addEventListener('submit', function(e) {
            const count = document.querySelectorAll('.pickup-checkbox:checked').length;
            if (!confirm(`Apakah Anda yakin ingin menyerahkan ${count} pickup ke admin?`)) {
                e.preventDefault();
            }
        });

        // Initialize
        updateSummary();
    </script>
</body>
</html>
