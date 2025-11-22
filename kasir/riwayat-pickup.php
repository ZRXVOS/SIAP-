<?php
/**
 * FILE: kasir/riwayat-pickup.php
 * FUNGSI: Riwayat pengambilan uang kasir
 * UPDATE: Label baru - Riwayat Pengambilan Uang
 */

require_once '../config.php';
check_login();
check_role('kasir');

$user_id = $_SESSION['user_id'];

// Filter parameters
$filter_outlet = isset($_GET['outlet']) ? clean_input($_GET['outlet']) : '';
$filter_status = isset($_GET['status']) ? clean_input($_GET['status']) : '';
$filter_dari = isset($_GET['dari']) ? clean_input($_GET['dari']) : date('Y-m-01');
$filter_sampai = isset($_GET['sampai']) ? clean_input($_GET['sampai']) : date('Y-m-d');

// Build query
$where = ["p.recorded_by = $user_id"];

if (!empty($filter_outlet)) {
    $where[] = "p.outlet_id = " . intval($filter_outlet);
}

if (!empty($filter_status)) {
    $where[] = "p.status = '" . $conn->real_escape_string($filter_status) . "'";
}

if (!empty($filter_dari)) {
    $where[] = "DATE(p.pickup_date) >= '$filter_dari'";
}

if (!empty($filter_sampai)) {
    $where[] = "DATE(p.pickup_date) <= '$filter_sampai'";
}

$where_clause = implode(' AND ', $where);

// Get data
$query = "SELECT p.*, o.outlet_name
          FROM pickups p
          JOIN outlets o ON p.outlet_id = o.id
          WHERE $where_clause
          ORDER BY p.pickup_date DESC
          LIMIT 100";
$result = $conn->query($query);

// Get summary
$query_summary = "SELECT
    COUNT(*) as total_transaksi,
    COALESCE(SUM(amount_taken), 0) as total_amount
    FROM pickups p
    WHERE $where_clause";
$result_summary = $conn->query($query_summary);
$summary = $result_summary->fetch_assoc();

// Get outlets for filter
$query_outlets = "SELECT * FROM outlets WHERE is_active = 1 ORDER BY outlet_name";
$result_outlets = $conn->query($query_outlets);
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Riwayat Pengambilan Uang - LondriPedia Laundry</title>
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

        .header h1 {
            font-size: 20px;
        }

        .back-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
        }

        .container {
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 20px;
        }

        .filter-box {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }

        .filter-group label {
            display: block;
            margin-bottom: 5px;
            font-size: 13px;
            color: #666;
            font-weight: 500;
        }

        .filter-group select,
        .filter-group input {
            width: 100%;
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }

        .btn-filter {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
        }

        .btn-reset {
            padding: 10px 20px;
            background: #6b7280;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
            text-decoration: none;
            display: inline-block;
        }

        .summary-box {
            background: #f0f9ff;
            border: 2px solid #3b82f6;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
            align-items: center;
        }

        .summary-item {
            text-align: center;
        }

        .summary-label {
            font-size: 13px;
            color: #666;
            margin-bottom: 5px;
        }

        .summary-value {
            font-size: 24px;
            font-weight: bold;
            color: #3b82f6;
        }

        .data-table {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow-x: auto;
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

        .badge.unknown {
            background: #f3f4f6;
            color: #6b7280;
        }

        @media (max-width: 768px) {
            .filter-grid {
                grid-template-columns: 1fr;
            }

            .summary-box {
                flex-direction: column;
                gap: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Riwayat Pengambilan Uang</h1>
        <a href="dashboard.php" class="back-btn">← Kembali</a>
    </div>

    <div class="container">
        <!-- Filter -->
        <div class="filter-box">
            <form method="GET" action="">
                <div class="filter-grid">
                    <div class="filter-group">
                        <label>Outlet</label>
                        <select name="outlet">
                            <option value="">Semua Outlet</option>
                            <?php while ($outlet = $result_outlets->fetch_assoc()): ?>
                                <option value="<?php echo $outlet['id']; ?>" <?php echo $filter_outlet == $outlet['id'] ? 'selected' : ''; ?>>
                                    <?php echo htmlspecialchars($outlet['outlet_name']); ?>
                                </option>
                            <?php endwhile; ?>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Status</label>
                        <select name="status">
                            <option value="">Semua Status</option>
                            <option value="pending_handover" <?php echo $filter_status == 'pending_handover' ? 'selected' : ''; ?>>Belum Disetor</option>
                            <option value="handed_over" <?php echo $filter_status == 'handed_over' ? 'selected' : ''; ?>>Sudah Disetor</option>
                            <option value="validated" <?php echo $filter_status == 'validated' ? 'selected' : ''; ?>>Tervalidasi</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Dari Tanggal</label>
                        <input type="date" name="dari" value="<?php echo htmlspecialchars($filter_dari); ?>">
                    </div>

                    <div class="filter-group">
                        <label>Sampai Tanggal</label>
                        <input type="date" name="sampai" value="<?php echo htmlspecialchars($filter_sampai); ?>">
                    </div>
                </div>

                <button type="submit" class="btn-filter">🔍 Filter</button>
                <a href="riwayat-pickup.php" class="btn-reset">🔄 Reset</a>
            </form>
        </div>

        <!-- Summary -->
        <div class="summary-box">
            <div class="summary-item">
                <div class="summary-label">Total Transaksi</div>
                <div class="summary-value"><?php echo number_format($summary['total_transaksi'], 0, ',', '.'); ?></div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Total Pengambilan</div>
                <div class="summary-value"><?php echo format_rupiah($summary['total_amount']); ?></div>
            </div>
        </div>

        <!-- Data Table -->
        <div class="data-table">
            <?php if ($result->num_rows > 0): ?>
                <table>
                    <thead>
                        <tr>
                            <th>Tanggal</th>
                            <th>Outlet</th>
                            <th>Jumlah</th>
                            <th>Catatan</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php while ($row = $result->fetch_assoc()): ?>
                            <tr>
                                <td><?php echo date('d/m/Y H:i', strtotime($row['pickup_date'])); ?></td>
                                <td><?php echo htmlspecialchars($row['outlet_name']); ?></td>
                                <td><strong><?php echo format_rupiah($row['amount_taken']); ?></strong></td>
                                <td><?php echo htmlspecialchars($row['notes'] ?? '-'); ?></td>
                                <td>
                                    <?php
                                    // Status mapping dengan pengecekan
                                    $status_map = [
                                        'pending_handover' => ['Belum Disetor', 'pending'],
                                        'handed_over' => ['Sudah Disetor', 'handed'],
                                        'validated' => ['Tervalidasi', 'validated']
                                    ];

                                    // Cek apakah status ada dan valid
                                    $current_status = $row['status'] ?? '';
                                    if (isset($status_map[$current_status])) {
                                        $status = $status_map[$current_status];
                                    } else {
                                        // Default jika status tidak dikenali
                                        $status = ['Status Unknown', 'unknown'];
                                    }
                                    ?>
                                    <span class="badge <?php echo htmlspecialchars($status[1]); ?>">
                                        <?php echo htmlspecialchars($status[0]); ?>
                                    </span>
                                </td>
                            </tr>
                        <?php endwhile; ?>
                    </tbody>
                </table>
            <?php else: ?>
                <p style="text-align: center; color: #999; padding: 40px 0;">
                    Tidak ada data sesuai filter
                </p>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
