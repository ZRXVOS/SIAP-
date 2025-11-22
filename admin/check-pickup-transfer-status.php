<?php
/**
 * FILE: admin/check-pickup-transfer-status.php
 * FUNGSI: Cek detail 44 pickup yang tampil di halaman transfer
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🔍 Investigasi: 44 Pickup di Halaman Transfer</h2>";
echo "<style>
    body { font-family: monospace; padding: 20px; background: #f0f2f5; }
    table { border-collapse: collapse; width: 100%; margin: 15px 0; background: white; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 11px; }
    th { background: #4f46e5; color: white; position: sticky; top: 0; }
    .error { color: #dc2626; font-weight: bold; }
    .success { color: #16a34a; font-weight: bold; }
    .warning { color: #ea580c; font-weight: bold; }
    .info { color: #2563eb; font-weight: bold; }
    h3 { margin-top: 25px; border-bottom: 3px solid #4f46e5; padding-bottom: 8px; color: #4f46e5; }
    pre { background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd; }
</style>";

// Query yang sama persis dengan transfer.php
$query = "SELECT p.id, p.outlet_id, p.status, p.transfer_id, p.amount_taken, p.actual_amount_received,
                 p.revenue_date, p.pickup_date, p.created_at, o.outlet_name,
                 COALESCE(p.actual_amount_received, p.amount_taken) as final_amount
          FROM pickups p
          JOIN outlets o ON p.outlet_id = o.id
          WHERE p.status = 'validated'
          AND (p.transfer_id IS NULL OR p.transfer_id = 0)
          ORDER BY p.id ASC";

$result = $conn->query($query);

echo "<h3>Pickup yang Tampil di Halaman Transfer (Query Sama dengan transfer.php)</h3>";
echo "<pre>";
echo "Total: <span class='warning'>{$result->num_rows} pickup</span>\n";
echo "Query: " . str_replace("\n", " ", $query) . "\n";
echo "</pre>";

if ($result->num_rows > 0) {
    // Kategorisasi
    $with_transfer = 0;
    $without_transfer = 0;

    echo "<table>";
    echo "<tr>";
    echo "<th>ID</th>";
    echo "<th>Outlet</th>";
    echo "<th>Status</th>";
    echo "<th>Transfer ID</th>";
    echo "<th>Amount</th>";
    echo "<th>Revenue Date</th>";
    echo "<th>Created At</th>";
    echo "<th>Keterangan</th>";
    echo "</tr>";

    while ($p = $result->fetch_assoc()) {
        $has_transfer_id = ($p['transfer_id'] && $p['transfer_id'] > 0);

        if ($has_transfer_id) $with_transfer++;
        else $without_transfer++;

        echo "<tr" . ($has_transfer_id ? " style='background: #fee2e2;'" : "") . ">";
        echo "<td>#" . $p['id'] . "</td>";
        echo "<td>" . $p['outlet_name'] . "</td>";
        echo "<td><span class='warning'>" . $p['status'] . "</span></td>";

        if ($has_transfer_id) {
            echo "<td><span class='error'>#" . $p['transfer_id'] . "</span></td>";
        } else {
            echo "<td><span class='info'>NULL</span></td>";
        }

        echo "<td>Rp " . number_format($p['final_amount'], 0, ',', '.') . "</td>";
        echo "<td>" . ($p['revenue_date'] ?? 'NULL') . "</td>";
        echo "<td>" . $p['created_at'] . "</td>";

        if ($has_transfer_id) {
            echo "<td><span class='error'>⚠️ ANOMALI: Punya transfer_id tapi masih tampil!</span></td>";
        } else {
            echo "<td><span class='success'>Normal: Belum ditransfer</span></td>";
        }

        echo "</tr>";
    }

    echo "</table>";

    echo "<h3>Ringkasan</h3>";
    echo "<pre>";
    echo "├─ <span class='error'>Dengan transfer_id (ANOMALI): $with_transfer pickup</span>\n";
    echo "│  → Seharusnya tidak tampil di halaman transfer\n";
    echo "│  → Query sudah filter 'transfer_id IS NULL OR transfer_id = 0' tapi masih tampil\n";
    echo "│  → <span class='warning'>ADA BUG DI QUERY!</span>\n";
    echo "│\n";
    echo "└─ <span class='success'>Tanpa transfer_id (NORMAL): $without_transfer pickup</span>\n";
    echo "   → Memang belum ditransfer, boleh tampil\n";
    echo "</pre>";

    // Cek apakah ada yang transfer_id-nya 0 (string '0' vs int 0)
    if ($with_transfer > 0) {
        echo "<h3>Detail Anomali - Transfer ID yang Ada</h3>";

        $check_query = "SELECT p.id, p.transfer_id, t.id as actual_transfer_id, t.created_at as transfer_date
                       FROM pickups p
                       LEFT JOIN transfers t ON p.transfer_id = t.id
                       WHERE p.status = 'validated'
                       AND p.transfer_id IS NOT NULL
                       AND p.transfer_id != 0
                       ORDER BY p.id ASC";

        $check_result = $conn->query($check_query);

        if ($check_result->num_rows > 0) {
            echo "<table>";
            echo "<tr><th>Pickup ID</th><th>transfer_id (di pickup)</th><th>Transfer Exists?</th><th>Transfer Date</th></tr>";

            while ($c = $check_result->fetch_assoc()) {
                echo "<tr>";
                echo "<td>#" . $c['id'] . "</td>";
                echo "<td>" . $c['transfer_id'] . "</td>";

                if ($c['actual_transfer_id']) {
                    echo "<td><span class='success'>✓ Ada (Transfer #" . $c['actual_transfer_id'] . ")</span></td>";
                    echo "<td>" . $c['transfer_date'] . "</td>";
                } else {
                    echo "<td><span class='error'>✗ Transfer tidak ditemukan!</span></td>";
                    echo "<td>-</td>";
                }

                echo "</tr>";
            }

            echo "</table>";
        }

        echo "<h3>🔧 ACTION REQUIRED</h3>";
        echo "<pre>";
        echo "<span class='error'>MASALAH: Query filter tidak bekerja dengan benar!</span>\n\n";
        echo "Solusi:\n";
        echo "1. Cek tipe data kolom transfer_id (INT vs VARCHAR?)\n";
        echo "2. Update semua pickup yang punya transfer_id jadi status 'transferred'\n";
        echo "</pre>";
    }

} else {
    echo "<pre><span class='success'>✅ Halaman transfer sudah kosong!</span></pre>";
}

echo "<br><br>";
echo "<a href='transfer.php' style='padding: 10px 20px; background: #10b981; color: white; text-decoration: none; border-radius: 8px; margin-right: 10px;'>← Kembali ke Transfer</a>";
echo "<a href='dashboard.php' style='padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;'>Dashboard</a>";
?>
