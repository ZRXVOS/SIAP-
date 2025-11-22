<?php
/**
 * FILE: admin/validasi.php
 * FUNGSI: Validasi penerimaan uang dari kasir - MODERN & COMPACT DESIGN
 * VERSION: 2.0 - Enhanced UX dengan Hidden Notes
 */

require_once '../config.php';
check_login();
check_role('admin');

$success = '';
$error = '';
$user_id = $_SESSION['user_id'];

// Proses validasi PER PICKUP (bukan per handover)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    $pickup_id = intval($_POST['pickup_id']);

    if ($_POST['action'] === 'validate') {
        $actual_amount = floatval(str_replace(['.', ','], '', $_POST['actual_amount']));
        $validation_notes = clean_input($_POST['validation_notes'] ?? '');

        // Get pickup data
        $query = "SELECT p.*, h.id as handover_id, h.pickup_ids
                  FROM pickups p
                  JOIN handovers h ON FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', ''))
                  WHERE p.id = $pickup_id AND p.status = 'handed_over'";
        $result = $conn->query($query);

        if ($result && $result->num_rows > 0) {
            $pickup = $result->fetch_assoc();
            $amount_taken = $pickup['amount_taken'];
            $difference = $actual_amount - $amount_taken;
            $handover_id = $pickup['handover_id'];

            $conn->begin_transaction();
            try {
                // Update pickup
                $stmt = $conn->prepare("UPDATE pickups SET status = 'validated', actual_amount_received = ?, updated_at = NOW() WHERE id = ?");
                $stmt->bind_param("di", $actual_amount, $pickup_id);
                $stmt->execute();

                // Cek apakah semua pickup di handover ini sudah validated
                $pickup_ids = json_decode($pickup['pickup_ids'], true);
                if (!empty($pickup_ids)) {
                    $ids_string = implode(',', array_map('intval', $pickup_ids));
                    $pending_count = $conn->query("SELECT COUNT(*) as c FROM pickups WHERE id IN ($ids_string) AND status != 'validated'")->fetch_assoc()['c'];

                    // Jika semua pickup sudah validated, update handover juga
                    if ($pending_count == 0) {
                        $conn->query("UPDATE handovers SET status = 'validated', validated_by = $user_id, validated_at = NOW() WHERE id = $handover_id");
                    }
                }

                $conn->commit();
                $success = "Validasi berhasil! Pickup #$pickup_id - Jumlah diterima: " . format_rupiah($actual_amount) . ($difference != 0 ? ", Selisih: " . format_rupiah($difference) : "");

            } catch (Exception $e) {
                $conn->rollback();
                $error = $e->getMessage();
            }
        } else {
            $error = "Pickup tidak ditemukan atau sudah divalidasi!";
        }

    } elseif ($_POST['action'] === 'reject') {
        // Tolak pickup - kembalikan ke pending_handover
        $conn->begin_transaction();
        try {
            $query = "SELECT p.*, h.id as handover_id, h.pickup_ids
                      FROM pickups p
                      JOIN handovers h ON FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', ''))
                      WHERE p.id = $pickup_id";
            $result = $conn->query($query);

            if ($result && $result->num_rows > 0) {
                $pickup = $result->fetch_assoc();
                $handover_id = $pickup['handover_id'];

                // Update pickup kembali ke pending_handover
                $conn->query("UPDATE pickups SET status = 'pending_handover', updated_at = NOW() WHERE id = $pickup_id");

                // Cek apakah masih ada pickup lain di handover ini
                $pickup_ids = json_decode($pickup['pickup_ids'], true);
                if (!empty($pickup_ids)) {
                    $ids_string = implode(',', array_map('intval', $pickup_ids));
                    $remaining_count = $conn->query("SELECT COUNT(*) as c FROM pickups WHERE id IN ($ids_string) AND status = 'handed_over'")->fetch_assoc()['c'];

                    // Jika tidak ada lagi pickup yang handed_over, update handover jadi rejected
                    if ($remaining_count == 0) {
                        $conn->query("UPDATE handovers SET status = 'rejected', validated_by = $user_id, validated_at = NOW() WHERE id = $handover_id");
                    }
                }

                $conn->commit();
                $success = "Pickup #$pickup_id ditolak dan dikembalikan ke kasir.";
            }
        } catch (Exception $e) {
            $conn->rollback();
            $error = $e->getMessage();
        }
    }
}

// Filter
$filter_outlet = isset($_GET['outlet']) ? intval($_GET['outlet']) : 0;

// Get PICKUPS from handovers pending validation (tampilkan per pickup, bukan per handover)
$query = "SELECT p.id as pickup_id,
          p.outlet_id,
          p.pickup_date,
          p.amount_taken,
          o.outlet_name,
          h.id as handover_id,
          h.created_at as handover_created_at,
          h.notes as handover_notes
          FROM pickups p
          JOIN handovers h ON FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', ''))
          JOIN outlets o ON p.outlet_id = o.id
          WHERE p.status = 'handed_over'";
if ($filter_outlet > 0) $query .= " AND p.outlet_id = $filter_outlet";
$query .= " ORDER BY h.created_at ASC, p.pickup_date ASC";
$result = $conn->query($query);

$outlets = $conn->query("SELECT * FROM outlets WHERE is_active = 1");
$total = $conn->query("SELECT COUNT(*) as c, COALESCE(SUM(amount_taken), 0) as t FROM pickups WHERE status = 'handed_over'")->fetch_assoc();
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validasi Penerimaan - LondriPedia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            font-size: 14px;
            color: #333;
        }

        .header {
            background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
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

        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

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
        .summary-text .count { color: #8b5cf6; font-weight: 700; font-size: 18px; }
        .summary-text .amount { color: #8b5cf6; font-weight: 600; }

        .filter select {
            padding: 8px 14px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 13px;
            background: white;
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .filter select:focus {
            outline: none;
            border-color: #8b5cf6;
        }

        /* Table Container */
        .table-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
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
        }

        tr:hover {
            background: #faf5ff;
            border-left: 4px solid #8b5cf6;
        }

        .pickup-id {
            font-weight: 600;
            color: #334155;
            font-size: 14px;
        }

        /* Outlet Badge */
        .outlet-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 4px;
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
            text-decoration: underline;
            text-decoration-style: dotted;
            position: relative;
        }

        .outlet-with-notes::after {
            content: "💬";
            margin-left: 4px;
            font-size: 12px;
        }

        .outlet-with-notes:hover {
            transform: scale(1.08);
            text-decoration-style: solid;
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

        /* Action Buttons */
        .action-buttons {
            display: flex;
            gap: 8px;
        }

        .btn-action {
            padding: 8px 12px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 600;
        }

        .btn-validate {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }
        .btn-validate:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        }

        .btn-reject {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
        }
        .btn-reject:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(239,68,68,0.3);
        }

        /* Modal/Popup */
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
            animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
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

        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #f1f5f9;
        }

        .info-row:last-child { border-bottom: none; }

        .info-label {
            font-size: 13px;
            color: #64748b;
        }

        .info-value {
            font-size: 14px;
            font-weight: 600;
            color: #334155;
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

        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            transition: border-color 0.2s;
        }

        .form-group input:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #8b5cf6;
            box-shadow: 0 0 0 3px rgba(139,92,246,0.1);
        }

        .form-group textarea {
            resize: vertical;
            min-height: 60px;
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

        .btn-primary {
            background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(139,92,246,0.3);
        }

        .btn-secondary {
            background: #f1f5f9;
            color: #64748b;
        }
        .btn-secondary:hover {
            background: #e2e8f0;
        }

        /* Notes Popup */
        .notes-popup {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 16px;
            border-radius: 8px;
            margin: 16px 0;
        }

        .notes-popup .label {
            font-size: 12px;
            color: #92400e;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .notes-popup .text {
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
            .action-buttons { flex-direction: column; }
            .btn-action { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>✅ Validasi Penerimaan</h1>
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
                📊 Menunggu validasi: <span class="count"><?php echo $total['c']; ?></span> pickup
                &nbsp;•&nbsp;
                Total: <span class="amount"><?php echo format_rupiah($total['t']); ?></span>
            </div>
            <form class="filter" method="GET">
                <select name="outlet" onchange="this.form.submit()">
                    <option value="0">🔍 Semua Outlet</option>
                    <?php while ($o = $outlets->fetch_assoc()): ?>
                        <option value="<?php echo $o['id']; ?>" <?php echo $filter_outlet == $o['id'] ? 'selected' : ''; ?>>
                            <?php echo $o['outlet_name']; ?>
                        </option>
                    <?php endwhile; ?>
                </select>
            </form>
        </div>

        <?php if ($result->num_rows > 0): ?>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>OUTLET</th>
                        <th>PERIODE</th>
                        <th>TGL SETOR</th>
                        <th>JUMLAH</th>
                        <th>AKSI</th>
                    </tr>
                </thead>
                <tbody>
                    <?php while ($p = $result->fetch_assoc()):
                        $periode_date = date('d/m/y', strtotime($p['pickup_date']));
                        $tgl_setor = date('d/m/y', strtotime($p['handover_created_at']));
                        $has_notes = !empty($p['handover_notes']);

                        // Determine outlet class
                        $outlet_class = (stripos($p['outlet_name'], 'monyonyo') !== false) ? 'outlet-monyonyo' : 'outlet-londripedia';
                        $note_class = $has_notes ? 'outlet-with-notes' : '';
                        $onclick = $has_notes ? "showNotes('{$p['pickup_id']}', '" . htmlspecialchars(addslashes($p['handover_notes'])) . "')" : '';
                    ?>
                    <tr>
                        <td><span class="pickup-id">#<?php echo $p['pickup_id']; ?></span></td>
                        <td>
                            <span class="outlet-badge <?php echo $outlet_class; ?> <?php echo $note_class; ?>"
                                  onclick="<?php echo $onclick; ?>">
                                <?php echo htmlspecialchars($p['outlet_name']); ?>
                            </span>
                        </td>
                        <td class="date-text">📅 <?php echo $periode_date; ?></td>
                        <td class="date-text">✋ <?php echo $tgl_setor; ?></td>
                        <td><span class="amount">💰 <?php echo format_rupiah($p['amount_taken']); ?></span></td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn-action btn-validate"
                                        onclick="showValidateModal(<?php echo $p['pickup_id']; ?>, '<?php echo addslashes($p['outlet_name']); ?>', <?php echo $p['amount_taken']; ?>, '<?php echo $periode_date; ?>', '<?php echo $tgl_setor; ?>')">
                                    ✓
                                </button>
                                <button class="btn-action btn-reject"
                                        onclick="confirmReject(<?php echo $p['pickup_id']; ?>, '<?php echo addslashes($p['outlet_name']); ?>', <?php echo $p['amount_taken']; ?>)">
                                    ✗
                                </button>
                            </div>
                        </td>
                    </tr>
                    <?php endwhile; ?>
                </tbody>
            </table>
        </div>
        <?php else: ?>
        <div class="table-container">
            <div class="empty-state">
                <div class="icon">🎉</div>
                <h3>Semua Sudah Tervalidasi!</h3>
                <p>Tidak ada pickup yang menunggu validasi</p>
            </div>
        </div>
        <?php endif; ?>
    </div>

    <!-- Modal Validasi -->
    <div id="validateModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                ✅ Validasi Pickup <span id="modalPickupId"></span>
            </div>
            <div class="modal-body">
                <div class="info-row">
                    <span class="info-label">Outlet:</span>
                    <span class="info-value" id="modalOutlet"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Periode:</span>
                    <span class="info-value" id="modalPeriode"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Tanggal Setor:</span>
                    <span class="info-value" id="modalTglSetor"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Total Dilaporkan:</span>
                    <span class="info-value" id="modalTotalDilaporkan" style="color: #8b5cf6;"></span>
                </div>

                <form id="validateForm" method="POST">
                    <input type="hidden" name="action" value="validate">
                    <input type="hidden" name="pickup_id" id="validatePickupId">

                    <div class="form-group">
                        <label>💰 Jumlah Diterima</label>
                        <input type="text" name="actual_amount" id="actualAmount" placeholder="Rp 0" required>
                    </div>

                    <div class="form-group">
                        <label>💬 Catatan Validasi (opsional)</label>
                        <textarea name="validation_notes" placeholder="Tulis catatan jika ada selisih atau hal penting lainnya..."></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-modal btn-secondary" onclick="closeModal('validateModal')">Batal</button>
                <button type="submit" form="validateForm" class="btn-modal btn-primary">✅ Validasi</button>
            </div>
        </div>
    </div>

    <!-- Modal Notes -->
    <div id="notesModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                💬 Catatan Pickup <span id="notesPickupId"></span>
            </div>
            <div class="modal-body">
                <div class="notes-popup">
                    <div class="label">Catatan dari Kasir:</div>
                    <div class="text" id="notesContent"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-modal btn-secondary" onclick="closeModal('notesModal')">Tutup</button>
            </div>
        </div>
    </div>

    <!-- Modal Reject -->
    <div id="rejectModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                ❌ Tolak Setoran
            </div>
            <div class="modal-body">
                <p style="margin-bottom: 16px; color: #64748b;">Yakin tolak pickup ini?</p>
                <div class="info-row">
                    <span class="info-label">Pickup:</span>
                    <span class="info-value" id="rejectPickupId"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Outlet:</span>
                    <span class="info-value" id="rejectOutlet"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Jumlah:</span>
                    <span class="info-value" id="rejectAmount" style="color: #ef4444;"></span>
                </div>

                <form id="rejectForm" method="POST">
                    <input type="hidden" name="action" value="reject">
                    <input type="hidden" name="pickup_id" id="rejectFormPickupId">
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-modal btn-secondary" onclick="closeModal('rejectModal')">Batal</button>
                <button type="submit" form="rejectForm" class="btn-modal btn-primary" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">❌ Ya, Tolak</button>
            </div>
        </div>
    </div>

    <script>
        function formatRupiah(n) {
            return 'Rp ' + n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        }

        function showValidateModal(id, outlet, amount, periode, tglSetor) {
            document.getElementById('modalPickupId').textContent = '#' + id;
            document.getElementById('modalOutlet').textContent = outlet;
            document.getElementById('modalPeriode').textContent = periode;
            document.getElementById('modalTglSetor').textContent = tglSetor;
            document.getElementById('modalTotalDilaporkan').textContent = formatRupiah(amount);
            document.getElementById('validatePickupId').value = id;
            document.getElementById('actualAmount').value = amount;
            document.getElementById('validateModal').classList.add('show');
        }

        function showNotes(id, notes) {
            document.getElementById('notesPickupId').textContent = '#' + id;
            document.getElementById('notesContent').textContent = notes;
            document.getElementById('notesModal').classList.add('show');
        }

        function confirmReject(id, outlet, amount) {
            document.getElementById('rejectPickupId').textContent = '#' + id;
            document.getElementById('rejectOutlet').textContent = outlet;
            document.getElementById('rejectAmount').textContent = formatRupiah(amount);
            document.getElementById('rejectFormPickupId').value = id;
            document.getElementById('rejectModal').classList.add('show');
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.remove('show');
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.classList.remove('show');
            }
        }

        // Format rupiah input
        document.getElementById('actualAmount').addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9]/g, '');
            if (value) {
                e.target.value = parseInt(value);
            }
        });
    </script>
</body>
</html>
