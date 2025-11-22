<?php
/**
 * FILE: admin/transfer.php
 * FUNGSI: Transfer per pickup - MINIMALIS & USER FRIENDLY
 * VERSION: 2.0 - Simplified UX
 */

require_once '../config.php';
check_login();
check_role('admin');

$success = '';
$error = '';
$user_id = $_SESSION['user_id'];

// Proses transfer
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['pickup_ids'])) {
    $pickup_ids = $_POST['pickup_ids'];
    $notes = clean_input($_POST['notes'] ?? '');

    // Tanggal transfer otomatis (hari ini)
    $transfer_date = date('Y-m-d');

    // Account destination dan transfer method tidak wajib (bisa NULL)
    $account_destination = '';
    $transfer_method = '';

    if (empty($pickup_ids)) {
        $error = "Pilih minimal 1 pickup!";
    } else {
        $ids_string = implode(',', array_map('intval', $pickup_ids));

        $sum_query = "SELECT COUNT(*) as c, COALESCE(SUM(COALESCE(actual_amount_received, amount_taken)), 0) as t
                      FROM pickups WHERE id IN ($ids_string) AND status = 'validated'";
        $sum_result = $conn->query($sum_query);
        $sum = $sum_result->fetch_assoc();

        if ($sum['c'] != count($pickup_ids)) {
            $error = "Beberapa pickup tidak valid!";
        } else {
            $total_transferred = $sum['t'];
            $conn->begin_transaction();

            try {
                $pickup_ids_json = json_encode(array_map('intval', $pickup_ids));
                $handover_ids_json = json_encode([]);

                $stmt = $conn->prepare("INSERT INTO transfers (transfer_date, pickup_ids, handover_ids, total_transferred, account_destination, transfer_method, notes, recorded_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW())");
                $stmt->bind_param("sssdsssi", $transfer_date, $pickup_ids_json, $handover_ids_json, $total_transferred, $account_destination, $transfer_method, $notes, $user_id);

                if (!$stmt->execute()) throw new Exception($stmt->error);

                $transfer_id = $stmt->insert_id;
                $stmt->close();

                $conn->query("UPDATE pickups SET status = 'transferred', transfer_id = $transfer_id, updated_at = NOW() WHERE id IN ($ids_string)");
                $conn->commit();

                $success = "Transfer berhasil! " . count($pickup_ids) . " pickup, total " . format_rupiah($total_transferred);

            } catch (Exception $e) {
                $conn->rollback();
                $error = $e->getMessage();
            }
        }
    }
}

// Filter
$filter_outlet = isset($_GET['outlet']) ? intval($_GET['outlet']) : 0;

// Get pickup validated
$query = "SELECT p.*, o.outlet_name,
                 COALESCE(p.actual_amount_received, p.amount_taken) as final_amount
          FROM pickups p
          JOIN outlets o ON p.outlet_id = o.id
          WHERE p.status = 'validated'";
if ($filter_outlet > 0) $query .= " AND p.outlet_id = $filter_outlet";
$query .= " ORDER BY p.revenue_date ASC, o.outlet_name ASC";
$result = $conn->query($query);

$outlets = $conn->query("SELECT * FROM outlets WHERE is_active = 1");
$total = $conn->query("SELECT COUNT(*) as c, COALESCE(SUM(COALESCE(actual_amount_received, amount_taken)), 0) as t FROM pickups WHERE status = 'validated'")->fetch_assoc();

// Riwayat
$history = $conn->query("SELECT t.*, u.full_name FROM transfers t LEFT JOIN users u ON t.recorded_by = u.id ORDER BY t.created_at DESC LIMIT 5");
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transfer ke Rekening</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            font-size: 14px;
            color: #333;
        }

        .header {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
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
        }
        .alert-success { background: #d1fae5; color: #065f46; border-left: 4px solid #10b981; }
        .alert-error { background: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444; }

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
        .summary-text .count { color: #10b981; font-weight: 700; font-size: 18px; }
        .summary-text .amount { color: #10b981; font-weight: 600; }

        .filter select {
            padding: 8px 14px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 13px;
            background: white;
            cursor: pointer;
        }

        /* Selection Bar */
        .selection-bar {
            background: white;
            border-radius: 12px;
            padding: 12px 20px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .selection-bar label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 13px;
            color: #374151;
        }
        .selection-bar input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .selection-info { font-size: 13px; color: #64748b; }
        .selection-info .highlight {
            color: #10b981;
            font-weight: 700;
            font-size: 15px;
        }

        /* Table */
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
            padding: 12px 16px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: middle;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #fafbfc; }
        tr.selected { background: #f0fdf4; }

        td input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        .pickup-id { font-weight: 600; color: #334155; }

        .outlet-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .outlet-1 { background: #dcfce7; color: #166534; }
        .outlet-2 { background: #dbeafe; color: #1e40af; }

        .date-text { color: #64748b; font-size: 13px; }
        .amount { font-weight: 600; color: #10b981; font-size: 14px; }

        /* Transfer Form - NEW MINIMALIST DESIGN */
        .transfer-form {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 16px;
            display: none;
        }
        .transfer-form.show { display: block; }

        .transfer-form h3 {
            font-size: 16px;
            margin-bottom: 16px;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }

        .summary-box {
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .summary-box h4 {
            font-size: 13px;
            color: #065f46;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .summary-box ul {
            list-style: none;
            padding: 0;
        }

        .summary-box li {
            font-size: 14px;
            color: #047857;
            padding: 4px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .summary-box li::before {
            content: "•";
            color: #10b981;
            font-weight: bold;
            font-size: 16px;
        }

        .form-group {
            margin-bottom: 20px;
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
            padding: 12px 14px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            min-height: 80px;
        }

        .form-group textarea:focus {
            outline: none;
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16,185,129,0.1);
        }

        .btn-transfer {
            padding: 14px 32px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            transition: all 0.2s;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn-transfer:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        }

        /* History */
        .history-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .history-section h3 {
            font-size: 14px;
            margin-bottom: 12px;
            color: #64748b;
        }
        .history-item {
            padding: 12px 0;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
        }
        .history-item:last-child { border-bottom: none; }
        .history-info { color: #64748b; }
        .history-info strong { color: #334155; }
        .history-amount { font-weight: 700; color: #10b981; font-size: 14px; }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }
        .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
        .empty-state h3 { font-size: 16px; color: #334155; margin-bottom: 4px; }
        .empty-state a { color: #10b981; text-decoration: none; }

        @media (max-width: 768px) {
            .container { padding: 12px; }
            th, td { padding: 10px 12px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>💸 Transfer ke Rekening</h1>
        <a href="dashboard.php" class="back-btn">← Kembali</a>
    </div>

    <div class="container">
        <?php if ($success): ?>
            <div class="alert alert-success">✓ <?php echo $success; ?></div>
        <?php endif; ?>
        <?php if ($error): ?>
            <div class="alert alert-error">! <?php echo $error; ?></div>
        <?php endif; ?>

        <div class="top-section">
            <div class="summary-text">
                Siap transfer: <span class="count"><?php echo $total['c']; ?></span> pickup
                &nbsp;•&nbsp;
                Total: <span class="amount"><?php echo format_rupiah($total['t']); ?></span>
            </div>
            <form class="filter" method="GET">
                <select name="outlet" onchange="this.form.submit()">
                    <option value="0">Semua Outlet</option>
                    <?php while ($o = $outlets->fetch_assoc()): ?>
                        <option value="<?php echo $o['id']; ?>" <?php echo $filter_outlet == $o['id'] ? 'selected' : ''; ?>>
                            <?php echo $o['outlet_name']; ?>
                        </option>
                    <?php endwhile; ?>
                </select>
            </form>
        </div>

        <?php if ($result->num_rows > 0): ?>
        <form method="POST" id="transferForm">
            <div class="selection-bar">
                <label>
                    <input type="checkbox" id="selectAll" onchange="toggleAll()">
                    Pilih Semua
                </label>
                <div class="selection-info">
                    Dipilih: <span class="highlight" id="selectedCount">0</span> pickup
                    &nbsp;•&nbsp;
                    Total: <span class="highlight" id="selectedTotal">Rp 0</span>
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width:40px"></th>
                            <th>ID</th>
                            <th>Outlet</th>
                            <th>Periode</th>
                            <th>Tgl Ambil</th>
                            <th>Jumlah</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php while ($p = $result->fetch_assoc()):
                            $tgl_ambil = $p['pickup_date'] ? date('d/m/y', strtotime($p['pickup_date'])) : '-';
                            $periode = ($p['revenue_date'] && $p['revenue_date'] != '0000-00-00') ? date('d/m/y', strtotime($p['revenue_date'])) : $tgl_ambil;
                            $final_amount = $p['final_amount'] ?? $p['amount_taken'];
                        ?>
                        <tr onclick="toggleRow(this)">
                            <td><input type="checkbox" name="pickup_ids[]" value="<?php echo $p['id']; ?>" data-amount="<?php echo $final_amount; ?>" onchange="updateTotal()" onclick="event.stopPropagation()"></td>
                            <td><span class="pickup-id">#<?php echo $p['id']; ?></span></td>
                            <td><span class="outlet-badge outlet-<?php echo $p['outlet_id']; ?>"><?php echo $p['outlet_name']; ?></span></td>
                            <td class="date-text"><?php echo $periode; ?></td>
                            <td class="date-text"><?php echo $tgl_ambil; ?></td>
                            <td><span class="amount"><?php echo format_rupiah($final_amount); ?></span></td>
                        </tr>
                        <?php endwhile; ?>
                    </tbody>
                </table>
            </div>

            <div class="transfer-form" id="transferBox">
                <h3>✅ Konfirmasi Transfer</h3>

                <div class="summary-box">
                    <h4>📋 Ringkasan Transfer</h4>
                    <ul>
                        <li><span id="summaryCount">0</span> pickup terpilih</li>
                        <li>Total yang akan ditransfer: <strong id="summaryTotal">Rp 0</strong></li>
                        <li>Tanggal transfer: <strong><?php echo date('d F Y'); ?></strong></li>
                    </ul>
                </div>

                <div class="form-group">
                    <label>💬 Catatan Transfer (opsional)</label>
                    <textarea name="notes" placeholder=""></textarea>
                </div>

                <button type="submit" class="btn-transfer" onclick="return confirm('Proses transfer sekarang?')">
                    💸 Proses Transfer Sekarang
                </button>
            </div>
        </form>
        <?php else: ?>
        <div class="table-container">
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>Belum Ada Pickup Siap Transfer</h3>
                <p>Validasi pickup terlebih dahulu</p>
                <p style="margin-top:8px"><a href="validasi.php">→ Ke Halaman Validasi</a></p>
            </div>
        </div>
        <?php endif; ?>

        <?php if ($history && $history->num_rows > 0): ?>
        <div class="history-section">
            <h3>📋 Riwayat Transfer Terakhir</h3>
            <?php while ($h = $history->fetch_assoc()):
                $pickup_count = $h['pickup_ids'] ? count(json_decode($h['pickup_ids'], true) ?? []) : 0;
            ?>
            <div class="history-item">
                <div class="history-info">
                    <strong>#<?php echo $h['id']; ?></strong> •
                    <?php echo date('d/m/y', strtotime($h['transfer_date'])); ?> •
                    <?php echo $pickup_count; ?> pickup
                    <?php if ($h['notes']): ?>
                        • <?php echo htmlspecialchars(substr($h['notes'], 0, 30)) . (strlen($h['notes']) > 30 ? '...' : ''); ?>
                    <?php endif; ?>
                </div>
                <div class="history-amount"><?php echo format_rupiah($h['total_transferred']); ?></div>
            </div>
            <?php endwhile; ?>
        </div>
        <?php endif; ?>
    </div>

    <script>
        function formatRupiah(n) { return 'Rp ' + n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "."); }

        function toggleAll() {
            const checked = document.getElementById('selectAll').checked;
            document.querySelectorAll('input[name="pickup_ids[]"]').forEach(cb => {
                cb.checked = checked;
                cb.closest('tr').classList.toggle('selected', checked);
            });
            updateTotal();
        }

        function toggleRow(tr) {
            const cb = tr.querySelector('input[type="checkbox"]');
            cb.checked = !cb.checked;
            tr.classList.toggle('selected', cb.checked);
            updateTotal();
        }

        function updateTotal() {
            let count = 0, total = 0;
            document.querySelectorAll('input[name="pickup_ids[]"]:checked').forEach(cb => {
                count++;
                total += parseFloat(cb.dataset.amount) || 0;
            });

            // Update selection bar
            document.getElementById('selectedCount').textContent = count;
            document.getElementById('selectedTotal').textContent = formatRupiah(total);

            // Update summary box
            document.getElementById('summaryCount').textContent = count;
            document.getElementById('summaryTotal').textContent = formatRupiah(total);

            // Show/hide form
            document.getElementById('transferBox').classList.toggle('show', count > 0);
        }
    </script>
</body>
</html>
