<?php
/**
 * FILE: admin/dashboard.php
 * FUNGSI: Dashboard admin dengan ringkasan keuangan
 * VERSION: 3.2 - FIX QUERY SALDO KAS & BELUM DIVALIDASI dari tabel PICKUPS
 */

require_once '../config.php';
check_login();
check_role('admin');

$user_id = $_SESSION['user_id'];

// Check delete success message
if (isset($_SESSION['delete_success'])) {
    $success = $_SESSION['delete_success'];
    unset($_SESSION['delete_success']);
}

// FIX: 1. SALDO KAS DI TANGAN = pickup dengan status 'validated' (belum ditransfer)
$query_saldo = "SELECT COALESCE(SUM(COALESCE(actual_amount_received, amount_taken)), 0) as total
                FROM pickups
                WHERE status = 'validated'";
$result_saldo = $conn->query($query_saldo);
$saldo_kas = $result_saldo->fetch_assoc()['total'];

// FIX: 2. PENDING VALIDASI = pickup dengan status 'handed_over' (sudah disetor, belum divalidasi)
$query_pending = "SELECT COUNT(*) as count, COALESCE(SUM(COALESCE(actual_amount_received, amount_taken)), 0) as total
                  FROM pickups
                  WHERE status = 'handed_over'";
$result_pending = $conn->query($query_pending);
$pending_data = $result_pending->fetch_assoc();

// 3. TRANSFER BULAN INI
$query_transfer = "SELECT COALESCE(SUM(total_transferred), 0) as total
                   FROM transfers
                   WHERE MONTH(transfer_date) = MONTH(CURDATE())
                   AND YEAR(transfer_date) = YEAR(CURDATE())";
$result_transfer = $conn->query($query_transfer);
$transfer_bulan_ini = $result_transfer->fetch_assoc()['total'];

// 4. PENDING DELETE REQUESTS
$query_delete_req = "SELECT COUNT(*) as count FROM delete_requests WHERE status = 'pending'";
$result_delete_req = $conn->query($query_delete_req);
$delete_req_count = $result_delete_req->fetch_assoc()['count'];

// 5. SETORAN TERBARU (10 record) - dari handovers
$query_recent = "SELECT h.id, h.handover_date, h.total_amount, h.actual_amount_received, h.difference, h.status,
                 GROUP_CONCAT(DISTINCT o.outlet_name ORDER BY o.outlet_name SEPARATOR ', ') as outlets
                 FROM handovers h
                 LEFT JOIN pickups p ON FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', ''))
                 LEFT JOIN outlets o ON p.outlet_id = o.id
                 GROUP BY h.id
                 ORDER BY h.created_at DESC
                 LIMIT 10";
$result_recent = $conn->query($query_recent);

// 6. NOTIFIKASI BELUM DIBACA
$query_notif = "SELECT COUNT(*) as count FROM notifications WHERE user_id = $user_id AND is_read = 0";
$result_notif = $conn->query($query_notif);
$notif_count = $result_notif->fetch_assoc()['count'];
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Admin - LondriPedia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header-content { max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 20px; }
        .header p { font-size: 13px; opacity: 0.9; margin-top: 3px; }
        .header-right { display: flex; gap: 15px; align-items: center; }
        .notif-badge { position: relative; font-size: 24px; cursor: pointer; }
        .notif-count { position: absolute; top: -5px; right: -8px; background: #ef4444; color: white; border-radius: 10px; padding: 2px 6px; font-size: 11px; font-weight: bold; }
        .logout-btn { background: rgba(255,255,255,0.2); color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 14px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }

        .alert-success { background: #d1fae5; color: #065f46; border: 1px solid #10b981; padding: 12px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }

        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .summary-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .summary-card .label { font-size: 13px; color: #666; margin-bottom: 8px; }
        .summary-card .value { font-size: 28px; font-weight: bold; color: #333; margin-bottom: 5px; }
        .summary-card .subvalue { font-size: 14px; color: #10b981; }
        .summary-card.saldo .value { color: #10b981; }
        .summary-card.pending .value { color: #f59e0b; }
        .summary-card.transfer .value { color: #667eea; }

        .action-buttons { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .action-btn { display: block; text-align: center; padding: 20px; background: white; border-radius: 12px; text-decoration: none; color: #333; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; position: relative; }
        .action-btn:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .action-btn .icon { font-size: 32px; margin-bottom: 10px; }
        .action-btn .text { font-weight: 600; font-size: 16px; }
        .action-btn .badge { position: absolute; top: 10px; right: 10px; background: #ef4444; color: white; border-radius: 20px; padding: 4px 10px; font-size: 12px; font-weight: bold; }
        .action-btn.primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }

        .section { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #333; }

        table { width: 100%; border-collapse: collapse; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-size: 13px; color: #666; font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }

        .outlet-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 4px; }
        .badge-monyonyo { background: #dbeafe; color: #1e40af; }
        .badge-londripedia { background: #fef3c7; color: #92400e; }

        .badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge.pending { background: #fef3c7; color: #d97706; }
        .badge.validated { background: #d1fae5; color: #059669; }
        .badge.transferred { background: #dbeafe; color: #2563eb; }

        @media (max-width: 768px) {
            .container { padding: 15px; }
            .summary-grid { grid-template-columns: 1fr; }
            table { font-size: 12px; }
            th, td { padding: 8px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div>
                <h1>Dashboard Admin</h1>
                <p>Selamat datang, <?php echo $_SESSION['full_name']; ?></p>
            </div>
            <div class="header-right">
                <div class="notif-badge">
                    🔔
                    <?php if ($notif_count > 0): ?>
                        <span class="notif-count"><?php echo $notif_count; ?></span>
                    <?php endif; ?>
                </div>
                <a href="../logout.php" class="logout-btn">Logout</a>
            </div>
        </div>
    </div>

    <div class="container">
        <?php if (isset($success)): ?>
            <div class="alert-success">✅ <?php echo $success; ?></div>
        <?php endif; ?>

        <!-- RINGKASAN KEUANGAN -->
        <div class="summary-grid">
            <div class="summary-card saldo">
                <div class="label">💰 Saldo Kas di Tangan</div>
                <div class="value"><?php echo format_rupiah($saldo_kas); ?></div>
                <div class="subvalue">Tersedia untuk transfer</div>
            </div>

            <div class="summary-card pending">
                <div class="label">⏳ Belum Divalidasi</div>
                <div class="value"><?php echo $pending_data['count']; ?></div>
                <div class="subvalue"><?php echo format_rupiah($pending_data['total']); ?></div>
            </div>

            <div class="summary-card transfer">
                <div class="label">💸 Transfer Bulan Ini</div>
                <div class="value"><?php echo format_rupiah($transfer_bulan_ini); ?></div>
                <div class="subvalue"><?php echo date('F Y'); ?></div>
            </div>
        </div>

        <!-- QUICK ACTIONS -->
        <div class="action-buttons">
            <a href="validasi.php" class="action-btn primary">
                <?php if ($pending_data['count'] > 0): ?>
                    <span class="badge"><?php echo $pending_data['count']; ?></span>
                <?php endif; ?>
                <div class="icon">✅</div>
                <div class="text">Validasi Setoran</div>
            </a>

            <a href="transfer.php" class="action-btn">
                <div class="icon">💸</div>
                <div class="text">Transfer Uang</div>
            </a>

            <a href="approve-delete.php" class="action-btn">
                <?php if ($delete_req_count > 0): ?>
                    <span class="badge"><?php echo $delete_req_count; ?></span>
                <?php endif; ?>
                <div class="icon">🗑️</div>
                <div class="text">Persetujuan Hapus</div>
            </a>

            <a href="laporan.php" class="action-btn">
                <div class="icon">📊</div>
                <div class="text">Laporan</div>
            </a>
        </div>

        <!-- SETORAN TERBARU -->
        <div class="section">
            <div class="section-title">📋 Setoran Terbaru</div>

            <?php if ($result_recent->num_rows > 0): ?>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Tanggal</th>
                                <th>Outlet</th>
                                <th>Total Dilaporkan</th>
                                <th>Aktual Diterima</th>
                                <th>Selisih</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php while ($row = $result_recent->fetch_assoc()): ?>
                                <tr>
                                    <td><?php echo date('d/m/Y H:i', strtotime($row['handover_date'])); ?></td>
                                    <td>
                                        <?php
                                        if ($row['outlets']) {
                                            $outlets = array_unique(explode(', ', $row['outlets']));
                                            foreach ($outlets as $outlet) {
                                                $badge_class = (stripos($outlet, 'monyonyo') !== false) ? 'badge-monyonyo' : 'badge-londripedia';
                                                echo "<span class='outlet-badge $badge_class'>$outlet</span>";
                                            }
                                        } else {
                                            echo '-';
                                        }
                                        ?>
                                    </td>
                                    <td><strong><?php echo format_rupiah($row['total_amount']); ?></strong></td>
                                    <td><?php echo $row['actual_amount_received'] ? format_rupiah($row['actual_amount_received']) : '-'; ?></td>
                                    <td>
                                        <?php if ($row['difference']): ?>
                                            <span style="color: <?php echo $row['difference'] < 0 ? '#ef4444' : '#10b981'; ?>">
                                                <?php echo format_rupiah($row['difference']); ?>
                                            </span>
                                        <?php else: ?>
                                            -
                                        <?php endif; ?>
                                    </td>
                                    <td>
                                        <?php
                                        $status_label = [
                                            'pending_validation' => ['Pending', 'pending'],
                                            'validated' => ['Tervalidasi', 'validated'],
                                            'transferred' => ['Ditransfer', 'transferred']
                                        ];
                                        $status = $status_label[$row['status']] ?? ['Unknown', 'pending'];
                                        ?>
                                        <span class="badge <?php echo $status[1]; ?>"><?php echo $status[0]; ?></span>
                                    </td>
                                </tr>
                            <?php endwhile; ?>
                        </tbody>
                    </table>
                </div>
            <?php else: ?>
                <p style="text-align: center; color: #999; padding: 40px 0;">
                    Belum ada data setoran
                </p>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
