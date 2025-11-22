<?php
/**
 * FILE: kasir/dashboard.php
 * FUNGSI: Dashboard untuk Kasir
 * UPDATE: Label baru - Pengambilan Uang & Setor ke Admin
 * FIX: Error handling untuk status yang tidak terdefinisi
 */

require_once '../config.php';
check_login();
check_role('kasir');

$user_id = $_SESSION['user_id'];

// Get total pengambilan hari ini
$today = date('Y-m-d');
$query_today = "SELECT COALESCE(SUM(amount_taken), 0) as total, COUNT(*) as count
                FROM pickups
                WHERE recorded_by = $user_id AND DATE(pickup_date) = '$today'";
$result_today = $conn->query($query_today);
$today_data = $result_today->fetch_assoc();

// Get total belum disetor
$query_pending = "SELECT COALESCE(SUM(amount_taken), 0) as total, COUNT(*) as count
                  FROM pickups
                  WHERE recorded_by = $user_id AND status = 'pending_handover'";
$result_pending = $conn->query($query_pending);
$pending_data = $result_pending->fetch_assoc();

// Get pengambilan 7 hari terakhir
$query_week = "SELECT DATE(pickup_date) as tanggal, SUM(amount_taken) as total
               FROM pickups
               WHERE recorded_by = $user_id
               AND pickup_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
               GROUP BY DATE(pickup_date)
               ORDER BY pickup_date DESC";
$result_week = $conn->query($query_week);

// Get pengambilan terbaru
$query_recent = "SELECT p.*, o.outlet_name
                 FROM pickups p
                 JOIN outlets o ON p.outlet_id = o.id
                 WHERE p.recorded_by = $user_id
                 ORDER BY p.created_at DESC
                 LIMIT 10";
$result_recent = $conn->query($query_recent);

// Get notifikasi belum dibaca
$query_notif = "SELECT COUNT(*) as count
                FROM notifications
                WHERE user_id = $user_id AND is_read = 0";
$result_notif = $conn->query($query_notif);
$notif_count = $result_notif->fetch_assoc()['count'];
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Kasir - LondriPedia Laundry</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f6fa;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header-left h1 {
            font-size: 20px;
            margin-bottom: 3px;
        }

        .header-left p {
            font-size: 13px;
            opacity: 0.9;
        }

        .header-right {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .notif-badge {
            position: relative;
            font-size: 24px;
            cursor: pointer;
        }

        .notif-count {
            position: absolute;
            top: -5px;
            right: -8px;
            background: #ef4444;
            color: white;
            border-radius: 10px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
        }

        .logout-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .summary-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .summary-card .label {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }

        .summary-card .value {
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }

        .summary-card .subvalue {
            font-size: 14px;
            color: #10b981;
        }

        .summary-card.today .value {
            color: #667eea;
        }

        .summary-card.pending .value {
            color: #f59e0b;
        }

        .action-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .action-btn {
            display: block;
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 12px;
            text-decoration: none;
            color: #333;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }

        .action-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .action-btn .icon {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .action-btn .text {
            font-weight: 600;
            font-size: 16px;
        }

        .action-btn.primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-size: 13px;
            color: #666;
            font-weight: 600;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 14px;
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }

        .badge.pending {
            background: #fef3c7;
            color: #d97706;
        }

        .badge.handed {
            background: #dbeafe;
            color: #2563eb;
        }

        .badge.validated {
            background: #d1fae5;
            color: #059669;
        }

        .badge.transferred {
            background: #e0e7ff;
            color: #6366f1;
        }

        .badge.unknown {
            background: #f3f4f6;
            color: #6b7280;
        }

        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }

            .summary-grid {
                grid-template-columns: 1fr;
            }

            table {
                font-size: 12px;
            }

            th, td {
                padding: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <h1>Dashboard Kasir</h1>
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

    <div class="container">
        <!-- Summary Cards -->
        <div class="summary-grid">
            <div class="summary-card today">
                <div class="label">💰 Pengambilan Hari Ini</div>
                <div class="value"><?php echo format_rupiah($today_data['total']); ?></div>
                <div class="subvalue"><?php echo $today_data['count']; ?> transaksi</div>
            </div>

            <div class="summary-card pending">
                <div class="label">⏳ Belum Disetor</div>
                <div class="value"><?php echo format_rupiah($pending_data['total']); ?></div>
                <div class="subvalue"><?php echo $pending_data['count']; ?> transaksi</div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
            <a href="input-pickup.php" class="action-btn primary">
                <div class="icon">💰</div>
                <div class="text">Input Pengambilan Uang</div>
            </a>

            <a href="handover.php" class="action-btn">
                <div class="icon">💵</div>
                <div class="text">Setor ke Admin</div>
            </a>

            <a href="riwayat-pickup.php" class="action-btn">
                <div class="icon">📋</div>
                <div class="text">Riwayat Pengambilan</div>
            </a>
        </div>

        <!-- Recent Pickups -->
        <div class="section">
            <div class="section-title">📊 Pengambilan Terbaru</div>

            <?php if ($result_recent->num_rows > 0): ?>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Tanggal</th>
                                <th>Outlet</th>
                                <th>Jumlah</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php while ($row = $result_recent->fetch_assoc()):
                                // FIX: Tambahkan semua status yang mungkin ada dan default handling
                                $status_map = [
                                    'pending_handover' => ['Belum Disetor', 'pending'],
                                    'handed_over' => ['Sudah Disetor', 'handed'],
                                    'validated' => ['Tervalidasi', 'validated'],
                                    'transferred' => ['Ditransfer', 'transferred']
                                ];

                                // FIX: Check jika status ada di map, jika tidak gunakan default
                                $current_status = $row['status'] ?? 'unknown';
                                if (isset($status_map[$current_status])) {
                                    $status = $status_map[$current_status];
                                } else {
                                    // Default untuk status yang tidak dikenal
                                    $status = [ucfirst(str_replace('_', ' ', $current_status)), 'unknown'];
                                }
                            ?>
                                <tr>
                                    <td><?php echo date('d/m/Y H:i', strtotime($row['pickup_date'])); ?></td>
                                    <td><?php echo $row['outlet_name']; ?></td>
                                    <td><strong><?php echo format_rupiah($row['amount_taken']); ?></strong></td>
                                    <td>
                                        <span class="badge <?php echo $status[1]; ?>"><?php echo $status[0]; ?></span>
                                    </td>
                                </tr>
                            <?php endwhile; ?>
                        </tbody>
                    </table>
                </div>
            <?php else: ?>
                <p style="text-align: center; color: #999; padding: 40px 0;">
                    Belum ada data pengambilan
                </p>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
