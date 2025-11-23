<?php
/**
 * FILE: admin/debug-selisih-calculation.php
 * PURPOSE: Debug script to investigate selisih calculation issue
 * Expected: Total selisih should be Rp300,000 (Rp250,000 + Rp50,000 from last 10 transactions)
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h1>Debug Selisih Calculation</h1>";
echo "<style>
    body { font-family: monospace; padding: 20px; }
    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    .highlight { background-color: #ffeb3b !important; }
    .error { color: red; font-weight: bold; }
    .success { color: green; font-weight: bold; }
</style>";

// Get all pickups with non-null actual_amount_received (belum ditransfer atau ada selisih)
echo "<h2>1. Pickups dengan actual_amount_received (yang sudah divalidasi/disetor)</h2>";
$query = "SELECT
    p.id,
    p.pickup_date,
    o.outlet_name,
    p.amount_taken as dilaporkan,
    p.actual_amount_received as aktual,
    (p.actual_amount_received - p.amount_taken) as selisih_raw,
    (COALESCE(p.actual_amount_received, 0) - p.amount_taken) as selisih_coalesce,
    p.status,
    p.created_at
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE p.actual_amount_received IS NOT NULL
ORDER BY p.id DESC
LIMIT 20";

$result = $conn->query($query);

echo "<table>";
echo "<tr>
    <th>ID</th>
    <th>Pickup Date</th>
    <th>Outlet</th>
    <th>Dilaporkan</th>
    <th>Aktual</th>
    <th>Selisih (Raw)</th>
    <th>Selisih (COALESCE)</th>
    <th>Status</th>
</tr>";

$total_selisih = 0;
$count = 0;
while ($row = $result->fetch_assoc()) {
    $selisih = $row['selisih_raw'];
    $total_selisih += $selisih;
    $count++;

    $highlight = ($selisih != 0) ? 'class="highlight"' : '';

    echo "<tr $highlight>";
    echo "<td>#{$row['id']}</td>";
    echo "<td>{$row['pickup_date']}</td>";
    echo "<td>{$row['outlet_name']}</td>";
    echo "<td>Rp " . number_format($row['dilaporkan'], 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['aktual'] ?? 0, 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['selisih_raw'] ?? 0, 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['selisih_coalesce'], 0, ',', '.') . "</td>";
    echo "<td>{$row['status']}</td>";
    echo "</tr>";
}
echo "</table>";

echo "<p><strong>Total Selisih (20 terakhir dengan actual != NULL): Rp " . number_format($total_selisih, 0, ',', '.') . "</strong></p>";
echo "<p>Jumlah records: $count</p>";

// Check specifically for records with non-zero selisih
echo "<h2>2. Pickups dengan SELISIH != 0 (ada perbedaan)</h2>";
$query2 = "SELECT
    p.id,
    p.pickup_date,
    o.outlet_name,
    p.amount_taken as dilaporkan,
    p.actual_amount_received as aktual,
    (p.actual_amount_received - p.amount_taken) as selisih,
    p.status,
    p.notes
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE p.actual_amount_received IS NOT NULL
    AND (p.actual_amount_received - p.amount_taken) != 0
ORDER BY p.id DESC
LIMIT 20";

$result2 = $conn->query($query2);

echo "<table>";
echo "<tr>
    <th>ID</th>
    <th>Pickup Date</th>
    <th>Outlet</th>
    <th>Dilaporkan</th>
    <th>Aktual</th>
    <th>Selisih</th>
    <th>Status</th>
    <th>Notes</th>
</tr>";

$total_selisih_nonzero = 0;
$count_nonzero = 0;
while ($row = $result2->fetch_assoc()) {
    $selisih = $row['selisih'];
    $total_selisih_nonzero += $selisih;
    $count_nonzero++;

    echo "<tr class='highlight'>";
    echo "<td>#{$row['id']}</td>";
    echo "<td>{$row['pickup_date']}</td>";
    echo "<td>{$row['outlet_name']}</td>";
    echo "<td>Rp " . number_format($row['dilaporkan'], 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['aktual'] ?? 0, 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['selisih'] ?? 0, 0, ',', '.') . "</td>";
    echo "<td>{$row['status']}</td>";
    echo "<td>" . (isset($row['notes']) ? substr($row['notes'], 0, 50) : '-') . "</td>";
    echo "</tr>";
}
echo "</table>";

echo "<p><strong>Total Selisih (hanya yang != 0): Rp " . number_format($total_selisih_nonzero, 0, ',', '.') . "</strong></p>";
echo "<p>Jumlah records dengan selisih: $count_nonzero</p>";

// Check current summary calculation from laporan.php
echo "<h2>3. Perhitungan Summary (seperti di laporan.php)</h2>";

// Default filter: bulan November 2025
$filter_dari = '2025-11-01';
$filter_sampai = date('Y-m-d');

$where = ["DATE(p.pickup_date) >= '$filter_dari'", "DATE(p.pickup_date) <= '$filter_sampai'"];
$where_clause = implode(' AND ', $where);

// Current calculation (WRONG?)
$query_summary_old = "SELECT
    COUNT(*) as total_transaksi,
    COALESCE(SUM(p.amount_taken), 0) as total_dilaporkan,
    COALESCE(SUM(p.actual_amount_received), 0) as total_aktual,
    COALESCE(SUM(p.actual_amount_received - p.amount_taken), 0) as total_selisih_old
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE $where_clause";

$result_old = $conn->query($query_summary_old);
$summary_old = $result_old->fetch_assoc();

// New calculation (CORRECT?)
$query_summary_new = "SELECT
    COUNT(*) as total_transaksi,
    COALESCE(SUM(p.amount_taken), 0) as total_dilaporkan,
    COALESCE(SUM(p.actual_amount_received), 0) as total_aktual,
    COALESCE(SUM(COALESCE(p.actual_amount_received, 0) - p.amount_taken), 0) as total_selisih_new
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE $where_clause";

$result_new = $conn->query($query_summary_new);
$summary_new = $result_new->fetch_assoc();

echo "<h3>Filter: $filter_dari s/d $filter_sampai</h3>";
echo "<table>";
echo "<tr>
    <th>Metric</th>
    <th>OLD Calculation (SUM(actual - taken))</th>
    <th>NEW Calculation (SUM(COALESCE(actual,0) - taken))</th>
    <th>Difference</th>
</tr>";

echo "<tr>";
echo "<td>Total Transaksi</td>";
echo "<td>" . number_format($summary_old['total_transaksi'], 0, ',', '.') . "</td>";
echo "<td>" . number_format($summary_new['total_transaksi'], 0, ',', '.') . "</td>";
echo "<td>-</td>";
echo "</tr>";

echo "<tr>";
echo "<td>Total Dilaporkan</td>";
echo "<td>Rp " . number_format($summary_old['total_dilaporkan'], 0, ',', '.') . "</td>";
echo "<td>Rp " . number_format($summary_new['total_dilaporkan'], 0, ',', '.') . "</td>";
echo "<td>-</td>";
echo "</tr>";

echo "<tr>";
echo "<td>Total Aktual</td>";
echo "<td>Rp " . number_format($summary_old['total_aktual'], 0, ',', '.') . "</td>";
echo "<td>Rp " . number_format($summary_new['total_aktual'], 0, ',', '.') . "</td>";
echo "<td>-</td>";
echo "</tr>";

echo "<tr class='highlight'>";
echo "<td><strong>Total Selisih</strong></td>";
echo "<td><strong>Rp " . number_format($summary_old['total_selisih_old'], 0, ',', '.') . "</strong></td>";
echo "<td><strong>Rp " . number_format($summary_new['total_selisih_new'], 0, ',', '.') . "</strong></td>";
echo "<td class='" . ($summary_old['total_selisih_old'] != $summary_new['total_selisih_new'] ? 'error' : 'success') . "'>";
echo "Rp " . number_format(abs($summary_old['total_selisih_old'] - $summary_new['total_selisih_new']), 0, ',', '.');
echo "</td>";
echo "</tr>";
echo "</table>";

// Add explanation
echo "<div style='background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0;'>";
echo "<h3 style='margin-top: 0; color: #856404;'>⚠️ PENJELASAN PERBEDAAN</h3>";
echo "<p><strong>OLD Calculation (BENAR untuk laporan.php):</strong></p>";
echo "<ul>";
echo "<li>Hanya menghitung pickup yang SUDAH disetor/divalidasi (actual_amount_received IS NOT NULL)</li>";
echo "<li>Total Selisih = Selisih AKTUAL antara yang dilaporkan vs yang diterima</li>";
echo "<li>Pickup yang belum disetor TIDAK dihitung karena belum ada nilai aktualnya</li>";
echo "<li style='color: green; font-weight: bold;'>✓ Ini adalah calculation yang BENAR untuk Total Selisih</li>";
echo "</ul>";
echo "<p><strong>NEW Calculation (SALAH jika digunakan):</strong></p>";
echo "<ul>";
echo "<li>Menghitung SEMUA pickup, termasuk yang belum disetor</li>";
echo "<li>Pickup yang belum disetor dianggap actual = 0, sehingga selisih = 0 - dilaporkan (negatif besar)</li>";
echo "<li>Perbedaan Rp " . number_format(abs($summary_old['total_selisih_old'] - $summary_new['total_selisih_new']), 0, ',', '.') . " = Total amount_taken dari pickup yang belum disetor</li>";
echo "<li style='color: red; font-weight: bold;'>✗ Ini TIDAK masuk akal karena kita belum terima uangnya</li>";
echo "</ul>";
echo "<p style='background: #d4edda; border-left: 4px solid #28a745; padding: 10px; margin-top: 15px;'>";
echo "<strong style='color: #155724;'>KESIMPULAN:</strong> laporan.php SUDAH BENAR menggunakan OLD calculation. ";
echo "Total Selisih Rp " . number_format($summary_old['total_selisih_old'], 0, ',', '.') . " adalah nilai yang tepat.";
echo "</p>";
echo "</div>";

// Check for the expected Rp300,000
echo "<h2>4. Cari 2 Transaksi dengan Selisih Rp250,000 dan Rp50,000</h2>";
$query_search = "SELECT
    p.id,
    p.pickup_date,
    o.outlet_name,
    p.amount_taken as dilaporkan,
    p.actual_amount_received as aktual,
    (p.actual_amount_received - p.amount_taken) as selisih,
    p.status,
    p.notes
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE p.actual_amount_received IS NOT NULL
    AND ((p.actual_amount_received - p.amount_taken) = 250000
         OR (p.actual_amount_received - p.amount_taken) = 50000
         OR (p.actual_amount_received - p.amount_taken) = -250000
         OR (p.actual_amount_received - p.amount_taken) = -50000)
ORDER BY p.id DESC";

$result_search = $conn->query($query_search);

if ($result_search->num_rows > 0) {
    echo "<table>";
    echo "<tr>
        <th>ID</th>
        <th>Pickup Date</th>
        <th>Outlet</th>
        <th>Dilaporkan</th>
        <th>Aktual</th>
        <th>Selisih</th>
        <th>Status</th>
    </tr>";

    while ($row = $result_search->fetch_assoc()) {
        echo "<tr class='highlight'>";
        echo "<td>#{$row['id']}</td>";
        echo "<td>{$row['pickup_date']}</td>";
        echo "<td>{$row['outlet_name']}</td>";
        echo "<td>Rp " . number_format($row['dilaporkan'], 0, ',', '.') . "</td>";
        echo "<td>Rp " . number_format($row['aktual'] ?? 0, 0, ',', '.') . "</td>";
        echo "<td><strong>Rp " . number_format($row['selisih'] ?? 0, 0, ',', '.') . "</strong></td>";
        echo "<td>{$row['status']}</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<p class='error'>Tidak ditemukan transaksi dengan selisih Rp250,000 atau Rp50,000</p>";
}

// Show pickups with actual != NULL (yang sudah disetor/divalidasi)
echo "<h2>5. Verifikasi: Total Selisih dari Semua Pickup dengan Actual != NULL</h2>";
$query_last10 = "SELECT
    p.id,
    p.pickup_date,
    o.outlet_name,
    p.amount_taken as dilaporkan,
    p.actual_amount_received as aktual,
    (p.actual_amount_received - p.amount_taken) as selisih,
    p.status
FROM pickups p
LEFT JOIN outlets o ON p.outlet_id = o.id
WHERE p.actual_amount_received IS NOT NULL
  AND DATE(p.pickup_date) >= '2025-11-01' AND DATE(p.pickup_date) <= '2025-11-23'
ORDER BY p.id DESC";

$result_last10 = $conn->query($query_last10);

echo "<table>";
echo "<tr>
    <th>ID</th>
    <th>Pickup Date</th>
    <th>Outlet</th>
    <th>Dilaporkan</th>
    <th>Aktual</th>
    <th>Selisih</th>
    <th>Status</th>
</tr>";

$total_selisih_last10 = 0;
while ($row = $result_last10->fetch_assoc()) {
    $selisih = $row['selisih'];
    $total_selisih_last10 += $selisih;

    $highlight = ($selisih != 0) ? 'class="highlight"' : '';

    echo "<tr $highlight>";
    echo "<td>#{$row['id']}</td>";
    echo "<td>{$row['pickup_date']}</td>";
    echo "<td>{$row['outlet_name']}</td>";
    echo "<td>Rp " . number_format($row['dilaporkan'], 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['aktual'] ?? 0, 0, ',', '.') . "</td>";
    echo "<td>Rp " . number_format($row['selisih'], 0, ',', '.') . "</td>";
    echo "<td>{$row['status']}</td>";
    echo "</tr>";
}
echo "</table>";

echo "<p><strong>Total Selisih dari semua pickup dengan actual != NULL: Rp " . number_format($total_selisih_last10, 0, ',', '.') . "</strong></p>";

if ($total_selisih_last10 == -300000) {
    echo "<p class='success'>✓ Total selisih = Rp " . number_format($total_selisih_last10, 0, ',', '.') . " (SESUAI dengan laporan.php!)</p>";
} else {
    echo "<p class='error'>✗ Total selisih = Rp " . number_format($total_selisih_last10, 0, ',', '.') . " (Expected: Rp -300.000)</p>";
}

echo "<p style='background: #e0f2fe; border-left: 4px solid #0284c7; padding: 10px; margin-top: 10px;'>";
echo "<strong>ℹ️ Catatan:</strong> Ini harus sama dengan 'Total Selisih' di section 3 (OLD Calculation) dan di laporan.php";
echo "</p>";

echo "<hr>";
echo "<p><a href='laporan.php'>← Kembali ke Laporan Pickup</a></p>";
?>
