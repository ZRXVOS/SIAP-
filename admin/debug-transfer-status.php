<?php
/**
 * FILE: admin/debug-transfer-status.php
 * FUNGSI: Debug untuk melihat status pickup dan transfer
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>Debug Transfer Status</h2>";
echo "<style>
    body { font-family: monospace; padding: 20px; }
    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }
    th { background: #4CAF50; color: white; }
    .error { color: red; font-weight: bold; }
    .success { color: green; font-weight: bold; }
    .warning { color: orange; font-weight: bold; }
    h3 { margin-top: 30px; border-bottom: 2px solid #333; padding-bottom: 5px; }
</style>";

// 1. CEK TRANSFER TERAKHIR
echo "<h3>1. Transfer Terakhir (10 record)</h3>";
$transfers = $conn->query("SELECT t.*, u.full_name
                          FROM transfers t
                          LEFT JOIN users u ON t.recorded_by = u.id
                          ORDER BY t.created_at DESC
                          LIMIT 10");

if ($transfers->num_rows > 0) {
    echo "<table>";
    echo "<tr><th>ID</th><th>Tanggal</th><th>Pickup IDs</th><th>Total</th><th>Recorded By</th><th>Created</th></tr>";
    while ($t = $transfers->fetch_assoc()) {
        $pickup_ids = json_decode($t['pickup_ids'], true);
        $pickup_count = is_array($pickup_ids) ? count($pickup_ids) : 0;
        echo "<tr>";
        echo "<td>#" . $t['id'] . "</td>";
        echo "<td>" . $t['transfer_date'] . "</td>";
        echo "<td>" . $pickup_count . " pickups: " . json_encode($pickup_ids) . "</td>";
        echo "<td>" . format_rupiah($t['total_transferred']) . "</td>";
        echo "<td>" . $t['full_name'] . "</td>";
        echo "<td>" . $t['created_at'] . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<p class='warning'>Tidak ada transfer di database!</p>";
}

// 2. CEK STATUS PICKUP
echo "<h3>2. Distribusi Status Pickup</h3>";
$status_count = $conn->query("SELECT status, COUNT(*) as count, SUM(amount_taken) as total
                              FROM pickups
                              GROUP BY status
                              ORDER BY count DESC");

echo "<table>";
echo "<tr><th>Status</th><th>Count</th><th>Total Amount</th></tr>";
while ($s = $status_count->fetch_assoc()) {
    echo "<tr>";
    echo "<td class='" . ($s['status'] == 'transferred' ? 'success' : 'warning') . "'>" . $s['status'] . "</td>";
    echo "<td>" . $s['count'] . "</td>";
    echo "<td>" . format_rupiah($s['total']) . "</td>";
    echo "</tr>";
}
echo "</table>";

// 3. CEK PICKUP DENGAN transfer_id TAPI STATUS BUKAN 'transferred'
echo "<h3>3. Pickup dengan transfer_id tapi status BUKAN 'transferred' (ANOMALI!)</h3>";
$anomali = $conn->query("SELECT id, outlet_id, status, transfer_id, amount_taken
                        FROM pickups
                        WHERE transfer_id IS NOT NULL
                        AND status != 'transferred'
                        LIMIT 20");

if ($anomali->num_rows > 0) {
    echo "<p class='error'>DITEMUKAN " . $anomali->num_rows . " pickup ANOMALI!</p>";
    echo "<table>";
    echo "<tr><th>Pickup ID</th><th>Outlet ID</th><th>Status</th><th>Transfer ID</th><th>Amount</th></tr>";
    while ($a = $anomali->fetch_assoc()) {
        echo "<tr class='error'>";
        echo "<td>#" . $a['id'] . "</td>";
        echo "<td>" . $a['outlet_id'] . "</td>";
        echo "<td>" . $a['status'] . "</td>";
        echo "<td>#" . $a['transfer_id'] . "</td>";
        echo "<td>" . format_rupiah($a['amount_taken']) . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<p class='success'>✓ Tidak ada anomali</p>";
}

// 4. CEK PICKUP YANG STATUSNYA 'transferred'
echo "<h3>4. Pickup dengan status 'transferred' (20 terakhir)</h3>";
$transferred = $conn->query("SELECT id, outlet_id, status, transfer_id, amount_taken, updated_at
                            FROM pickups
                            WHERE status = 'transferred'
                            ORDER BY updated_at DESC
                            LIMIT 20");

if ($transferred->num_rows > 0) {
    echo "<table>";
    echo "<tr><th>Pickup ID</th><th>Outlet ID</th><th>Transfer ID</th><th>Amount</th><th>Updated At</th></tr>";
    while ($tf = $transferred->fetch_assoc()) {
        echo "<tr>";
        echo "<td>#" . $tf['id'] . "</td>";
        echo "<td>" . $tf['outlet_id'] . "</td>";
        echo "<td>#" . ($tf['transfer_id'] ?? 'NULL') . "</td>";
        echo "<td>" . format_rupiah($tf['amount_taken']) . "</td>";
        echo "<td>" . $tf['updated_at'] . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<p class='error'>TIDAK ADA pickup dengan status 'transferred'!</p>";
}

// 5. CEK HANDOVER YANG STATUSNYA 'validated'
echo "<h3>5. Handover dengan status 'validated' (20 pertama)</h3>";
$handovers = $conn->query("SELECT id, pickup_ids, total_amount, actual_amount_received, difference, status, created_at
                          FROM handovers
                          WHERE status = 'validated'
                          ORDER BY created_at DESC
                          LIMIT 20");

if ($handovers->num_rows > 0) {
    echo "<table>";
    echo "<tr><th>Handover ID</th><th>Pickup Count</th><th>Total</th><th>Actual</th><th>Difference</th><th>Created</th></tr>";
    while ($h = $handovers->fetch_assoc()) {
        $pickup_ids = json_decode($h['pickup_ids'], true);
        $pickup_count = is_array($pickup_ids) ? count($pickup_ids) : 0;

        echo "<tr>";
        echo "<td>#" . $h['id'] . "</td>";
        echo "<td>" . $pickup_count . "</td>";
        echo "<td>" . format_rupiah($h['total_amount']) . "</td>";
        echo "<td>" . ($h['actual_amount_received'] ? format_rupiah($h['actual_amount_received']) : 'NULL') . "</td>";
        echo "<td>" . ($h['difference'] ? format_rupiah($h['difference']) : 'NULL') . "</td>";
        echo "<td>" . $h['created_at'] . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<p>Tidak ada handover 'validated'</p>";
}

echo "<br><br><a href='dashboard.php' style='padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;'>Kembali ke Dashboard</a>";
?>
