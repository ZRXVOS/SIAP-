<?php
/**
 * FILE: kasir/handover.php
 * FUNGSI: Serahkan uang ke admin - REDESIGN COMPACT & FAST
 * VERSION: 3.0 - Table Compact, Per Pickup, Fixed Telegram
 */

require_once '../config.php';
check_login();
check_role('kasir');

$success = '';
$error = '';
$user_id = $_SESSION['user_id'];

// Proses penyerahan
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['pickup_ids'])) {
    $pickup_ids = $_POST['pickup_ids'];
    $handover_date = date('Y-m-d H:i:s');
    $notes = clean_input($_POST['notes'] ?? '');

    if (empty($pickup_ids)) {
        $error = "Pilih minimal 1 pickup untuk diserahkan!";
    } else {
        // VALIDASI: Cek semua pickup dari outlet yang sama
        $ids_string = implode(',', array_map('intval', $pickup_ids));
        $query_check = "SELECT COUNT(DISTINCT outlet_id) as outlet_count,
                        MIN(o.outlet_name) as outlet_name
                        FROM pickups p
                        JOIN outlets o ON p.outlet_id = o.id
                        WHERE p.id IN ($ids_string)";
        $result_check = $conn->query($query_check);
        $check_data = $result_check->fetch_assoc();

        if ($check_data['outlet_count'] > 1) {
            $error = "Tidak boleh mencampur outlet dalam 1 setoran! Serahkan per outlet.";
        } else {
            // Hitung total amount
            $query_sum = "SELECT SUM(amount_taken) as total FROM pickups WHERE id IN ($ids_string) AND recorded_by = $user_id AND status = 'pending_handover'";
            $result_sum = $conn->query($query_sum);
            $total_amount = $result_sum->fetch_assoc()['total'];

            if ($total_amount > 0) {
                $conn->begin_transaction();

                try {
                    // Insert handover
                    $pickup_ids_json = json_encode(array_map('intval', $pickup_ids));
                    $stmt = $conn->prepare("INSERT INTO handovers (handover_date, pickup_ids, total_amount, notes, status, recorded_by, created_at) VALUES (?, ?, ?, ?, 'pending_validation', ?, NOW())");
                    $stmt->bind_param("ssdsi", $handover_date, $pickup_ids_json, $total_amount, $notes, $user_id);

                    if (!$stmt->execute()) throw new Exception($stmt->error);

                    $handover_id = $stmt->insert_id;
                    $stmt->close();

                    // Update status pickups
                    $conn->query("UPDATE pickups SET status = 'handed_over', updated_at = NOW() WHERE id IN ($ids_string)");

                    $conn->commit();

                    // FIXED: Kirim notifikasi Telegram
                    $outlet_name = $check_data['outlet_name'];
                    $telegram_sent = sendTelegramHandoverNotification($outlet_name, count($pickup_ids), $total_amount, $_SESSION['full_name'], $notes);

                    $success = "✅ Berhasil menyerahkan " . count($pickup_ids) . " pickup dengan total " . format_rupiah($total_amount) . "!";
                    if (!$telegram_sent) {
                        $success .= " (Notifikasi telegram gagal dikirim)";
                    }

                } catch (Exception $e) {
                    $conn->rollback();
                    $error = "Gagal menyimpan: " . $e->getMessage();
                }
            } else {
                $error = "Total tidak valid!";
            }
        }
    }
}

// Get pickup yang belum diserahkan
$query_pending = "SELECT p.*, o.outlet_name, o.id as outlet_id
                  FROM pickups p
                  JOIN outlets o ON p.outlet_id = o.id
                  WHERE p.recorded_by = $user_id AND p.status = 'pending_handover'
                  ORDER BY p.pickup_date DESC, o.outlet_name ASC";
$result_pending = $conn->query($query_pending);

$total_pending = $conn->query("SELECT COUNT(*) as c, COALESCE(SUM(amount_taken), 0) as t FROM pickups WHERE recorded_by = $user_id AND status = 'pending_handover'")->fetch_assoc();

/**
 * Fungsi kirim notifikasi Telegram
 */
function sendTelegramHandoverNotification($outlet, $count, $amount, $kasir_name, $notes) {
    // Cek apakah telegram diaktifkan
    if (!defined('TELEGRAM_BOT_TOKEN') || !defined('TELEGRAM_CHAT_ID')) {
        error_log("Telegram not configured");
        return false;
    }

    $bot_token = TELEGRAM_BOT_TOKEN;
    $chat_id = TELEGRAM_CHAT_ID;

    // Format pesan
    $message = "🤝 <b>SETORAN KASIR BARU</b>\n\n";
    $message .= "🏪 Outlet: <b>" . $outlet . "</b>\n";
    $message .= "💰 Total: <b>Rp " . number_format($amount, 0, ',', '.') . "</b>\n";
    $message .= "📦 Jumlah: " . $count . " pickup\n";
    $message .= "👤 Kasir: " . $kasir_name . "\n";
    if ($notes) {
        $message .= "💬 Catatan: " . $notes . "\n";
    }
    $message .= "\n⏳ Menunggu validasi admin";

    // Kirim via CURL
    $url = "https://api.telegram.org/bot{$bot_token}/sendMessage";

    $data = [
        'chat_id' => $chat_id,
        'text' => $message,
        'parse_mode' => 'HTML'
    ];

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($data));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); // For testing

    $result = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    // Log untuk debugging
    if ($http_code != 200 || $error) {
        error_log("Telegram error: HTTP {$http_code}, {$error}, Response: {$result}");
        return false;
    }

    return true;
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Serahkan ke Admin - LondriPedia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            font-size: 14px;
            color: #333;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .header h1 { font-size: 18px; font-weight: 600; }
        .back-btn {
            color: white;
            text-decoration: none;
            font-size: 13px;
            opacity: 0.9;
            padding: 6px 12px;
            background: rgba(255,255,255,0.15);
            border-radius: 6px;
            transition: all 0.2s;
        }
        .back-btn:hover { opacity: 1; background: rgba(255,255,255,0.25); }

        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }

        .alert {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
            animation: slideDown 0.3s ease-out;
        }
        .alert-success { background: #d1fae5; color: #065f46; border-left: 4px solid #10b981; }
        .alert-error { background: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444; }
        .alert-warning { background: #fef3c7; color: #92400e; border-left: 4px solid #f59e0b; }

        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Top Section */
        .top-section {
            background: white;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .summary-text { font-size: 14px; color: #555; }
        .summary-text .count { color: #667eea; font-weight: 700; font-size: 18px; }
        .summary-text .amount { color: #667eea; font-weight: 600; }

        .select-all-container {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 14px;
            color: #374151;
        }
        .select-all-container input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        /* Table Container */
        .table-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 16px;
        }

        table { width: 100%; border-collapse: collapse; }

        th {
            background: #f8fafc;
            padding: 14px 16px;
            text-align: left;
            font-size: 12px;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #e2e8f0;
        }

        td {
            padding: 16px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: middle;
        }

        tr:last-child td { border-bottom: none; }

        tr {
            transition: all 0.2s ease;
            cursor: pointer;
        }

        tr:hover {
            background: #f0f9ff;
            border-left: 4px solid #667eea;
        }

        tr.selected {
            background: #ede9fe;
        }

        tr.disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        td input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: #667eea;
        }

        /* Outlet Badge */
        .outlet-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            transition: transform 0.2s;
        }

        .outlet-badge:hover {
            transform: scale(1.05);
        }

        /* Monyonyo = Biru */
        .outlet-monyonyo {
            background: #dbeafe;
            color: #1e40af;
        }

        /* LondriPedia = Hijau */
        .outlet-londripedia {
            background: #d1fae5;
            color: #065f46;
        }

        /* Outlet dengan catatan - clickable */
        .outlet-with-notes {
            cursor: pointer;
            font-weight: 700;
            position: relative;
        }

        .outlet-with-notes::after {
            content: "💬";
            margin-left: 4px;
            font-size: 12px;
        }

        .outlet-with-notes:hover {
            transform: scale(1.08);
        }

        .date-text {
            color: #64748b;
            font-size: 13px;
        }

        .amount {
            font-weight: 600;
            color: #059669;
            font-size: 14px;
        }

        /* Summary Box - Hidden by default */
        .summary-box {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 16px;
            display: none;
            animation: slideUp 0.3s ease-out;
        }

        .summary-box.show { display: block; }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .summary-box h3 {
            font-size: 16px;
            margin-bottom: 16px;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }

        .summary-info {
            background: #ede9fe;
            border-left: 4px solid #667eea;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .summary-info h4 {
            font-size: 13px;
            color: #5b21b6;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .summary-info ul {
            list-style: none;
            padding: 0;
        }

        .summary-info li {
            font-size: 14px;
            color: #6d28d9;
            padding: 4px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .summary-info li::before {
            content: "•";
            color: #667eea;
            font-weight: bold;
            font-size: 16px;
        }

        .btn-container {
            display: flex;
            gap: 12px;
        }

        .btn {
            flex: 1;
            padding: 14px 32px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-notes {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
        }
        .btn-notes:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(245,158,11,0.3);
        }

        .btn-submit {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }
        .btn-submit:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            animation: fadeIn 0.3s ease-out;
        }

        .modal.show { display: flex; align-items: center; justify-content: center; }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background: white;
            border-radius: 16px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideUpModal 0.3s ease-out;
        }

        @keyframes slideUpModal {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .modal-header {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 8px;
            padding-bottom: 16px;
            border-bottom: 2px solid #f1f5f9;
        }

        .modal-body {
            margin-bottom: 20px;
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-group label {
            display: block;
            font-size: 13px;
            color: #64748b;
            margin-bottom: 8px;
            font-weight: 500;
        }

        .form-group textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            min-height: 80px;
            transition: border-color 0.2s;
        }

        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }

        .modal-footer {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }

        .btn-modal {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-modal-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-modal-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102,126,234,0.3);
        }

        .btn-modal-secondary {
            background: #f1f5f9;
            color: #64748b;
        }
        .btn-modal-secondary:hover {
            background: #e2e8f0;
        }

        /* Notes Popup */
        .notes-display {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 16px;
            border-radius: 8px;
        }

        .notes-display .label {
            font-size: 12px;
            color: #92400e;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .notes-display .text {
            font-size: 14px;
            color: #78350f;
            line-height: 1.5;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }
        .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
        .empty-state h3 { font-size: 16px; color: #334155; margin-bottom: 4px; }

        @media (max-width: 768px) {
            .container { padding: 12px; }
            th, td { padding: 12px; font-size: 12px; }
            .btn-container { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>💵 Serahkan ke Admin</h1>
        <a href="dashboard.php" class="back-btn">← Kembali</a>
    </div>

    <div class="container">
        <?php if ($success): ?>
            <div class="alert alert-success">✓ <?php echo $success; ?></div>
        <?php endif; ?>
        <?php if ($error): ?>
            <div class="alert alert-error">! <?php echo $error; ?></div>
        <?php endif; ?>

        <div class="alert alert-warning">
            ℹ️ <strong>Perhatian:</strong> Serahkan per outlet. Tidak boleh mencampur outlet dalam 1 setoran.
        </div>

        <div class="top-section">
            <div class="summary-text">
                📊 Belum disetor: <span class="count"><?php echo $total_pending['c']; ?></span> pickup
                &nbsp;•&nbsp;
                Total: <span class="amount"><?php echo format_rupiah($total_pending['t']); ?></span>
            </div>
            <label class="select-all-container">
                <input type="checkbox" id="selectAll">
                Pilih Semua
            </label>
        </div>

        <?php if ($result_pending->num_rows > 0): ?>
        <form method="POST" id="handoverForm">
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width:40px">☐</th>
                            <th>OUTLET</th>
                            <th>PERIODE</th>
                            <th>TGL AMBIL</th>
                            <th>JUMLAH</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php while ($p = $result_pending->fetch_assoc()):
                            $periode_date = $p['revenue_date'] && $p['revenue_date'] != '0000-00-00'
                                ? date('d/m/y', strtotime($p['revenue_date']))
                                : date('d/m/y', strtotime($p['pickup_date']));
                            $tgl_ambil = date('d/m/y', strtotime($p['pickup_date']));
                            $has_notes = !empty($p['notes']);
                            $outlet_class = (stripos($p['outlet_name'], 'monyonyo') !== false) ? 'outlet-monyonyo' : 'outlet-londripedia';
                            $note_class = $has_notes ? 'outlet-with-notes' : '';
                            $onclick = $has_notes ? "showPickupNotes('{$p['id']}', '" . htmlspecialchars(addslashes($p['notes'])) . "')" : '';
                        ?>
                        <tr class="pickup-row" data-outlet-id="<?php echo $p['outlet_id']; ?>" data-outlet-name="<?php echo htmlspecialchars($p['outlet_name']); ?>">
                            <td>
                                <input type="checkbox"
                                       name="pickup_ids[]"
                                       value="<?php echo $p['id']; ?>"
                                       class="pickup-checkbox"
                                       data-outlet-id="<?php echo $p['outlet_id']; ?>"
                                       data-outlet-name="<?php echo htmlspecialchars($p['outlet_name']); ?>"
                                       data-amount="<?php echo $p['amount_taken']; ?>"
                                       onclick="event.stopPropagation()">
                            </td>
                            <td>
                                <span class="outlet-badge <?php echo $outlet_class; ?> <?php echo $note_class; ?>"
                                      onclick="<?php echo $onclick; ?>">
                                    <?php echo htmlspecialchars($p['outlet_name']); ?>
                                </span>
                            </td>
                            <td class="date-text">📅 <?php echo $periode_date; ?></td>
                            <td class="date-text">✋ <?php echo $tgl_ambil; ?></td>
                            <td><span class="amount">💰 <?php echo format_rupiah($p['amount_taken']); ?></span></td>
                        </tr>
                        <?php endwhile; ?>
                    </tbody>
                </table>
            </div>

            <div class="summary-box" id="summaryBox">
                <h3>✅ Konfirmasi Serahkan</h3>
                <div class="summary-info">
                    <h4>📋 Ringkasan</h4>
                    <ul>
                        <li>Outlet: <strong id="selectedOutlet">-</strong></li>
                        <li>Pickup terpilih: <strong id="selectedCount">0</strong> item</li>
                        <li>Total diserahkan: <strong id="selectedTotal" style="color: #10b981;">Rp 0</strong></li>
                        <li>Tanggal serah: <strong><?php echo date('d F Y'); ?></strong></li>
                    </ul>
                </div>
                <div class="btn-container">
                    <button type="button" class="btn btn-notes" onclick="showNotesModal()">
                        💬 Tambah Catatan
                    </button>
                    <button type="button" class="btn btn-submit" onclick="confirmSubmit()">
                        💵 Serahkan ke Admin
                    </button>
                </div>
            </div>

            <input type="hidden" name="notes" id="hiddenNotes">
        </form>
        <?php else: ?>
        <div class="table-container">
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>Belum Ada Pickup</h3>
                <p>Tidak ada pengambilan yang belum diserahkan</p>
            </div>
        </div>
        <?php endif; ?>
    </div>

    <!-- Modal Notes Pickup -->
    <div id="pickupNotesModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                💬 Catatan Pickup <span id="pickupNotesId"></span>
            </div>
            <div class="modal-body">
                <div class="notes-display">
                    <div class="label">Catatan:</div>
                    <div class="text" id="pickupNotesContent"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-modal btn-modal-secondary" onclick="closeModal('pickupNotesModal')">Tutup</button>
            </div>
        </div>
    </div>

    <!-- Modal Add Notes -->
    <div id="addNotesModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                💬 Catatan untuk Admin
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>Catatan (Opsional)</label>
                    <textarea id="notesTextarea" placeholder="Tulis catatan untuk admin jika diperlukan..."></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-modal btn-modal-secondary" onclick="closeModal('addNotesModal')">Batal</button>
                <button type="button" class="btn-modal btn-modal-primary" onclick="saveNotes()">Simpan Catatan</button>
            </div>
        </div>
    </div>

    <script>
        const selectAllChk = document.getElementById('selectAll');
        const pickupCheckboxes = document.querySelectorAll('.pickup-checkbox');
        const pickupRows = document.querySelectorAll('.pickup-row');
        const summaryBox = document.getElementById('summaryBox');
        const selectedOutletEl = document.getElementById('selectedOutlet');
        const selectedCountEl = document.getElementById('selectedCount');
        const selectedTotalEl = document.getElementById('selectedTotal');

        let selectedOutletId = null;

        function formatRupiah(n) {
            return 'Rp ' + n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        }

        function updateUI() {
            let count = 0, total = 0;
            selectedOutletId = null;
            let selectedOutletName = '';

            // Hitung selected
            pickupCheckboxes.forEach(cb => {
                if (cb.checked) {
                    selectedOutletId = cb.dataset.outletId;
                    selectedOutletName = cb.dataset.outletName;
                    total += parseFloat(cb.dataset.amount);
                    count++;
                }
            });

            // Update disabled state
            pickupCheckboxes.forEach(cb => {
                const row = cb.closest('.pickup-row');
                if (selectedOutletId && cb.dataset.outletId !== selectedOutletId) {
                    cb.disabled = true;
                    row.classList.add('disabled');
                } else {
                    cb.disabled = false;
                    row.classList.remove('disabled');
                }
                row.classList.toggle('selected', cb.checked);
            });

            // Update select all
            const enabledCheckboxes = Array.from(pickupCheckboxes).filter(cb => !cb.disabled);
            const checkedEnabledCheckboxes = enabledCheckboxes.filter(cb => cb.checked);
            selectAllChk.checked = enabledCheckboxes.length > 0 && enabledCheckboxes.length === checkedEnabledCheckboxes.length;

            // Update summary
            if (count > 0) {
                summaryBox.classList.add('show');
                selectedOutletEl.textContent = selectedOutletName;
                selectedCountEl.textContent = count;
                selectedTotalEl.textContent = formatRupiah(total);
            } else {
                summaryBox.classList.remove('show');
            }
        }

        // Individual checkbox
        pickupCheckboxes.forEach(cb => {
            cb.addEventListener('change', updateUI);
        });

        // Click on row
        pickupRows.forEach(row => {
            row.addEventListener('click', e => {
                if (e.target.type === 'checkbox' || e.target.closest('.outlet-badge')) return;
                const cb = row.querySelector('.pickup-checkbox');
                if (!cb.disabled) {
                    cb.checked = !cb.checked;
                    updateUI();
                }
            });
        });

        // Select all
        selectAllChk.addEventListener('change', function() {
            pickupCheckboxes.forEach(cb => {
                if (!cb.disabled) {
                    cb.checked = this.checked;
                }
            });
            updateUI();
        });

        // Show pickup notes
        function showPickupNotes(id, notes) {
            event.stopPropagation();
            document.getElementById('pickupNotesId').textContent = '#' + id;
            document.getElementById('pickupNotesContent').textContent = notes;
            document.getElementById('pickupNotesModal').classList.add('show');
        }

        // Show notes modal
        function showNotesModal() {
            document.getElementById('addNotesModal').classList.add('show');
        }

        // Save notes
        function saveNotes() {
            const notes = document.getElementById('notesTextarea').value;
            document.getElementById('hiddenNotes').value = notes;
            closeModal('addNotesModal');
        }

        // Close modal
        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('show');
        }

        // Click outside to close
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.classList.remove('show');
            }
        }

        // Confirm submit
        function confirmSubmit() {
            const count = document.querySelectorAll('.pickup-checkbox:checked').length;
            const outlet = selectedOutletEl.textContent;
            const total = selectedTotalEl.textContent;

            if (confirm(`Serahkan ${count} pickup dari ${outlet} dengan total ${total}?`)) {
                document.getElementById('handoverForm').submit();
            }
        }
    </script>
</body>
</html>
