<?php
/**
 * FILE: admin/laporan.php
 * FUNGSI: Laporan Pickup dengan filter dan export Excel
 * VERSION: 1.2 - HIDE transaksi sebelum 20 Nov 2025 untuk akurasi data
 * NOTE: Minimum tanggal adalah 20 November 2025 untuk menghindari data lama yang bermasalah
 */

require_once '../config.php';
check_login();
check_role('admin');

// Filter parameters
// MINIMUM tanggal adalah 20 November 2025 untuk menghindari data lama yang bermasalah
$min_date = '2025-11-20';
$filter_dari = isset($_GET['dari']) ? clean_input($_GET['dari']) : $min_date;
$filter_sampai = isset($_GET['sampai']) ? clean_input($_GET['sampai']) : date('Y-m-d');
$filter_outlet = isset($_GET['outlet']) ? clean_input($_GET['outlet']) : '';
$filter_status = isset($_GET['status']) ? clean_input($_GET['status']) : '';

// Enforce minimum date - jangan tampilkan transaksi sebelum 20 Nov 2025
if ($filter_dari < $min_date) {
    $filter_dari = $min_date;
}

// Build WHERE clause
$where = ["DATE(p.pickup_date) >= '$filter_dari'", "DATE(p.pickup_date) <= '$filter_sampai'"];

if (!empty($filter_outlet)) {
    $where[] = "o.id = " . intval($filter_outlet);
}

if (!empty($filter_status)) {
    $where[] = "p.status = '" . $conn->real_escape_string($filter_status) . "'";
}

$where_clause = implode(' AND ', $where);

// Main query - get pickups with handover info
$query = "SELECT
    p.id,
    o.outlet_name,
    p.pickup_date as periode,
    p.created_at as tgl_input,
    p.pickup_date as tgl_ambil,
    h.validated_at as tgl_validasi,
    t.transfer_date as tgl_transfer,
    p.amount_taken as dilaporkan,
    COALESCE(p.actual_amount_received, 0) as aktual,
    (COALESCE(p.actual_amount_received, 0) - p.amount_taken) as selisih,
    p.status,
    p.notes as catatan
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
LEFT JOIN handovers h ON FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', ''))
LEFT JOIN transfers t ON FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(t.pickup_ids, '[', ''), ']', ''), '\"', ''))
WHERE $where_clause
ORDER BY p.pickup_date DESC, p.id DESC";

$result = $conn->query($query);

// Calculate summary
$query_summary = "SELECT
    COUNT(*) as total_transaksi,
    COALESCE(SUM(p.amount_taken), 0) as total_dilaporkan,
    COALESCE(SUM(p.actual_amount_received), 0) as total_aktual,
    COALESCE(SUM(p.actual_amount_received - p.amount_taken), 0) as total_selisih
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE $where_clause";

$result_summary = $conn->query($query_summary);
$summary = $result_summary->fetch_assoc();

// Get outlets for filter
$query_outlets = "SELECT * FROM outlets WHERE is_active = 1 ORDER BY outlet_name";
$result_outlets = $conn->query($query_outlets);

// Handle Excel export
if (isset($_GET['export']) && $_GET['export'] === 'excel') {
    header('Content-Type: application/vnd.ms-excel');
    header('Content-Disposition: attachment; filename="laporan-pickup-' . date('Y-m-d') . '.xls"');

    echo "<table border='1'>";
    echo "<tr style='background-color: #667eea; color: white; font-weight: bold;'>";
    echo "<th>ID</th><th>OUTLET</th><th>PERIODE</th><th>TGL INPUT</th><th>TGL AMBIL</th>";
    echo "<th>TGL VALIDASI</th><th>TGL TRANSFER</th><th>DILAPORKAN</th><th>AKTUAL</th>";
    echo "<th>SELISIH</th><th>STATUS</th><th>CATATAN</th>";
    echo "</tr>";

    $result->data_seek(0);
    while ($row = $result->fetch_assoc()) {
        $status_map = [
            'pending_handover' => 'Belum Disetor',
            'handed_over' => 'Sudah Disetor',
            'validated' => 'Valid',
            'transferred' => 'Transfer'
        ];
        $status_label = $status_map[$row['status']] ?? $row['status'];

        echo "<tr>";
        echo "<td>#" . $row['id'] . "</td>";
        echo "<td>" . htmlspecialchars($row['outlet_name']) . "</td>";
        echo "<td>" . date('d/m/Y', strtotime($row['periode'])) . "</td>";
        echo "<td>" . ($row['tgl_input'] ? date('d/m/Y', strtotime($row['tgl_input'])) : '-') . "</td>";
        echo "<td>" . ($row['tgl_ambil'] ? date('d/m/Y', strtotime($row['tgl_ambil'])) : '-') . "</td>";
        echo "<td>" . ($row['tgl_validasi'] ? date('d/m/Y', strtotime($row['tgl_validasi'])) : '-') . "</td>";
        echo "<td>" . ($row['tgl_transfer'] ? date('d/m/Y', strtotime($row['tgl_transfer'])) : '-') . "</td>";
        echo "<td>Rp " . number_format($row['dilaporkan'], 0, ',', '.') . "</td>";
        echo "<td>Rp " . number_format($row['aktual'], 0, ',', '.') . "</td>";
        echo "<td>Rp " . number_format($row['selisih'], 0, ',', '.') . "</td>";
        echo "<td>" . $status_label . "</td>";
        echo "<td>" . htmlspecialchars($row['catatan'] ?? '-') . "</td>";
        echo "</tr>";
    }

    echo "</table>";
    exit;
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laporan Pickup - LondriPedia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 20px; }
        .header p { font-size: 13px; opacity: 0.9; margin-top: 3px; }
        .back-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.2s;
        }
        .back-btn:hover { background: rgba(255,255,255,0.3); }

        .container { max-width: 1600px; margin: 20px auto; padding: 0 20px; }

        /* Filter Box */
        .filter-box {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
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
            font-weight: 600;
        }
        .filter-group input,
        .filter-group select {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            transition: border 0.2s;
        }
        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .filter-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .btn-success {
            background: #10b981;
            color: white;
        }
        .btn-success:hover {
            background: #059669;
        }
        .btn-secondary {
            background: #6b7280;
            color: white;
        }
        .btn-secondary:hover {
            background: #4b5563;
        }

        /* Summary Cards */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .summary-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
        }
        .summary-card.selisih {
            border-left-color: #ef4444;
        }
        .summary-card .label {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .summary-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .summary-card.selisih .value {
            color: #ef4444;
        }

        /* Table */
        .table-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 1200px;
        }
        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        th {
            padding: 14px 12px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        td {
            padding: 14px 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 13px;
            color: #333;
        }
        tbody tr:hover {
            background: #f9fafb;
        }

        .outlet-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-monyonyo {
            background: #dbeafe;
            color: #1e40af;
        }
        .badge-londripedia {
            background: #fef3c7;
            color: #92400e;
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge.pending { background: #fef3c7; color: #d97706; }
        .badge.handed { background: #e0e7ff; color: #4f46e5; }
        .badge.validated { background: #d1fae5; color: #059669; }
        .badge.transferred { background: #dbeafe; color: #2563eb; }

        .amount { font-weight: 600; }
        .amount.positive { color: #10b981; }
        .amount.negative { color: #ef4444; }
        .amount.zero { color: #6b7280; }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .empty-state .icon { font-size: 64px; margin-bottom: 15px; opacity: 0.5; }
        .empty-state .text { font-size: 16px; }

        @media (max-width: 768px) {
            .container { padding: 0 15px; }
            .filter-grid { grid-template-columns: 1fr; }
            .summary-grid { grid-template-columns: 1fr; }
            .filter-actions { flex-direction: column; }
            .btn { width: 100%; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div>
                <h1>📊 Laporan Pickup</h1>
                <p>Sunday, 23 November 2025 • 06:56</p>
            </div>
            <a href="dashboard.php" class="back-btn">← Kembali</a>
        </div>
    </div>

    <div class="container">
        <!-- Filter -->
        <div class="filter-box">
            <form method="GET" action="">
                <?php if ($filter_dari == $min_date && (!isset($_GET['dari']) || $_GET['dari'] < $min_date)): ?>
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin-bottom: 15px; border-radius: 8px; font-size: 13px;">
                    <strong>ℹ️ Info:</strong> Laporan ini hanya menampilkan transaksi dari <strong>20 November 2025</strong> ke atas untuk akurasi data.
                </div>
                <?php endif; ?>
                <div class="filter-grid">
                    <div class="filter-group">
                        <label>Dari Tanggal (Min: 20 Nov 2025)</label>
                        <input type="date" name="dari" value="<?php echo htmlspecialchars($filter_dari); ?>" min="<?php echo $min_date; ?>">
                    </div>

                    <div class="filter-group">
                        <label>Sampai Tanggal</label>
                        <input type="date" name="sampai" value="<?php echo htmlspecialchars($filter_sampai); ?>">
                    </div>

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
                            <option value="validated" <?php echo $filter_status == 'validated' ? 'selected' : ''; ?>>Valid</option>
                            <option value="transferred" <?php echo $filter_status == 'transferred' ? 'selected' : ''; ?>>Transfer</option>
                        </select>
                    </div>
                </div>

                <div class="filter-actions">
                    <button type="submit" class="btn btn-primary">🔍 Filter</button>
                    <a href="?dari=<?php echo htmlspecialchars($filter_dari); ?>&sampai=<?php echo htmlspecialchars($filter_sampai); ?>&outlet=<?php echo htmlspecialchars($filter_outlet); ?>&status=<?php echo htmlspecialchars($filter_status); ?>&export=excel" class="btn btn-success">📥 Excel</a>
                    <a href="laporan.php" class="btn btn-secondary">🔄 Reset</a>
                </div>
            </form>
        </div>

        <!-- Summary -->
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">Total Transaksi</div>
                <div class="value"><?php echo number_format($summary['total_transaksi'], 0, ',', '.'); ?></div>
            </div>

            <div class="summary-card">
                <div class="label">Total Dilaporkan</div>
                <div class="value">Rp <?php echo number_format($summary['total_dilaporkan'], 0, ',', '.'); ?></div>
            </div>

            <div class="summary-card">
                <div class="label">Total Aktual</div>
                <div class="value">Rp <?php echo number_format($summary['total_aktual'], 0, ',', '.'); ?></div>
            </div>

            <div class="summary-card selisih">
                <div class="label">Total Selisih</div>
                <div class="value">Rp <?php echo number_format($summary['total_selisih'], 0, ',', '.'); ?></div>
            </div>
        </div>

        <!-- Table -->
        <div class="table-container">
            <?php if ($result->num_rows > 0): ?>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>OUTLET</th>
                            <th>PERIODE</th>
                            <th>TGL INPUT</th>
                            <th>TGL AMBIL</th>
                            <th>TGL VALIDASI</th>
                            <th>TGL TRANSFER</th>
                            <th>DILAPORKAN</th>
                            <th>AKTUAL</th>
                            <th>SELISIH</th>
                            <th>STATUS</th>
                            <th>CATATAN</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php while ($row = $result->fetch_assoc()): ?>
                            <?php
                            $outlet_class = (stripos($row['outlet_name'], 'monyonyo') !== false) ? 'badge-monyonyo' : 'badge-londripedia';

                            $status_map = [
                                'pending_handover' => ['Belum Disetor', 'pending'],
                                'handed_over' => ['Sudah Disetor', 'handed'],
                                'validated' => ['Valid', 'validated'],
                                'transferred' => ['Transfer', 'transferred']
                            ];
                            $status = $status_map[$row['status']] ?? [$row['status'], 'pending'];

                            // Determine selisih color
                            $selisih_class = 'zero';
                            if ($row['selisih'] > 0) $selisih_class = 'positive';
                            if ($row['selisih'] < 0) $selisih_class = 'negative';
                            ?>
                            <tr>
                                <td><strong>#<?php echo $row['id']; ?></strong></td>
                                <td>
                                    <span class="outlet-badge <?php echo $outlet_class; ?>">
                                        <?php echo htmlspecialchars($row['outlet_name']); ?>
                                    </span>
                                </td>
                                <td><?php echo date('d/m/y', strtotime($row['periode'])); ?></td>
                                <td><?php echo $row['tgl_input'] ? date('d/m/y', strtotime($row['tgl_input'])) : '-'; ?></td>
                                <td><?php echo $row['tgl_ambil'] ? date('d/m/y', strtotime($row['tgl_ambil'])) : '-'; ?></td>
                                <td><?php echo $row['tgl_validasi'] ? date('d/m/y', strtotime($row['tgl_validasi'])) : '-'; ?></td>
                                <td><?php echo $row['tgl_transfer'] ? date('d/m/y', strtotime($row['tgl_transfer'])) : '-'; ?></td>
                                <td><span class="amount">Rp <?php echo number_format($row['dilaporkan'], 0, ',', '.'); ?></span></td>
                                <td><span class="amount">Rp <?php echo number_format($row['aktual'], 0, ',', '.'); ?></span></td>
                                <td>
                                    <span class="amount <?php echo $selisih_class; ?>">
                                        <?php if ($row['aktual'] > 0): ?>
                                            Rp <?php echo number_format($row['selisih'], 0, ',', '.'); ?>
                                        <?php else: ?>
                                            -
                                        <?php endif; ?>
                                    </span>
                                </td>
                                <td><span class="badge <?php echo $status[1]; ?>"><?php echo $status[0]; ?></span></td>
                                <td><?php echo $row['catatan'] ? htmlspecialchars(substr($row['catatan'], 0, 30)) . (strlen($row['catatan']) > 30 ? '...' : '') : '-'; ?></td>
                            </tr>
                        <?php endwhile; ?>
                    </tbody>
                </table>
            <?php else: ?>
                <div class="empty-state">
                    <div class="icon">📭</div>
                    <div class="text">Tidak ada data sesuai filter</div>
                </div>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
