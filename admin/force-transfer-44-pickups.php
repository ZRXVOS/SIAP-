<?php
/**
 * FILE: admin/force-transfer-44-pickups.php
 * FUNGSI: Memaksa transfer 44 pickup yang sudah ditransfer tapi tidak tercatat di database
 * WARNING: Hanya jalankan jika YAKIN pickup sudah ditransfer secara fisik!
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🔧 Force Transfer - 44 Pickup yang Tidak Tercatat</h2>";
echo "<style>
    body { font-family: monospace; padding: 20px; background: #f0f2f5; }
    table { border-collapse: collapse; width: 100%; margin: 15px 0; background: white; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }
    th { background: #dc2626; color: white; }
    .error { color: #dc2626; font-weight: bold; }
    .success { color: #16a34a; font-weight: bold; }
    .warning { color: #ea580c; font-weight: bold; }
    h3 { margin-top: 25px; border-bottom: 3px solid #dc2626; padding-bottom: 8px; color: #dc2626; }
    pre { background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd; line-height: 1.8; }
    .btn { display: inline-block; padding: 12px 24px; margin: 10px 5px; text-decoration: none; border-radius: 8px; font-weight: bold; }
    .btn-danger { background: #dc2626; color: white; }
    .btn-secondary { background: #6b7280; color: white; }
</style>";

echo "<pre>";

// STEP 1: Identifikasi pickup yang akan di-force transfer
echo "<h3>STEP 1: Identifikasi 44 Pickup</h3>";

$pickup_query = "SELECT p.id, p.outlet_id, p.amount_taken, p.actual_amount_received, o.outlet_name
                 FROM pickups p
                 JOIN outlets o ON p.outlet_id = o.id
                 WHERE p.status = 'validated'
                 AND (p.transfer_id IS NULL OR p.transfer_id = 0)
                 ORDER BY p.id ASC";

$pickups = $conn->query($pickup_query);
$total_pickups = $pickups->num_rows;
$total_amount = 0;
$pickup_ids = [];

echo "Ditemukan: <span class='warning'>$total_pickups pickup</span>\n\n";

echo "<table>";
echo "<tr><th>Pickup ID</th><th>Outlet</th><th>Amount</th></tr>";

while ($p = $pickups->fetch_assoc()) {
    $amount = $p['actual_amount_received'] ?? $p['amount_taken'];
    $total_amount += $amount;
    $pickup_ids[] = $p['id'];

    echo "<tr>";
    echo "<td>#" . $p['id'] . "</td>";
    echo "<td>" . $p['outlet_name'] . "</td>";
    echo "<td>Rp " . number_format($amount, 0, ',', '.') . "</td>";
    echo "</tr>";
}

echo "</table>";

echo "\n<span class='warning'>Total: Rp " . number_format($total_amount, 0, ',', '.') . "</span>\n";

// Konfirmasi
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo "\n";
    echo "═══════════════════════════════════════════════\n";
    echo "<span class='error'>⚠️  PERINGATAN!</span>\n";
    echo "═══════════════════════════════════════════════\n";
    echo "\n";
    echo "Script ini akan:\n";
    echo "1. Membuat record transfer BARU untuk $total_pickups pickup\n";
    echo "2. Update status pickup jadi 'transferred'\n";
    echo "3. Update handover jadi 'transferred'\n";
    echo "\n";
    echo "<span class='warning'>HANYA jalankan jika Anda YAKIN pickup ini sudah ditransfer!</span>\n";
    echo "\n";
    echo "</pre>";

    echo "<form method='POST'>";
    echo "<input type='hidden' name='confirm' value='yes'>";
    echo "<button type='submit' class='btn btn-danger' onclick='return confirm(\"Apakah Anda YAKIN ingin memaksa transfer $total_pickups pickup ini?\")'>⚠️ YA, FORCE TRANSFER SEKARANG</button>";
    echo "<a href='dashboard.php' class='btn btn-secondary'>← Batal</a>";
    echo "</form>";

    exit;
}

// STEP 2: Proses Force Transfer
echo "\n<h3>STEP 2: Membuat Record Transfer</h3>";

$conn->begin_transaction();

try {
    $user_id = $_SESSION['user_id'];
    $transfer_date = date('Y-m-d');
    $pickup_ids_json = json_encode($pickup_ids);
    $handover_ids_json = json_encode([]);
    $notes = "Force transfer - Dipaksa karena tidak tercatat di database (Total: $total_pickups pickup)";

    // Insert transfer record
    $stmt = $conn->prepare("INSERT INTO transfers (transfer_date, pickup_ids, handover_ids, total_transferred, account_destination, transfer_method, notes, recorded_by, created_at)
                           VALUES (?, ?, ?, ?, '', '', ?, ?, NOW())");
    $stmt->bind_param("ssddsi", $transfer_date, $pickup_ids_json, $handover_ids_json, $total_amount, $notes, $user_id);

    if (!$stmt->execute()) {
        throw new Exception("Gagal insert transfer: " . $stmt->error);
    }

    $transfer_id = $stmt->insert_id;
    $stmt->close();

    echo "✅ Transfer record created: <span class='success'>Transfer #$transfer_id</span>\n";
    echo "   Tanggal: $transfer_date\n";
    echo "   Total: Rp " . number_format($total_amount, 0, ',', '.') . "\n";
    echo "   Pickup: $total_pickups items\n\n";

    // STEP 3: Update pickup status
    echo "<h3>STEP 3: Update Status Pickup → 'transferred'</h3>";

    $ids_string = implode(',', $pickup_ids);
    $update_pickup = $conn->query("UPDATE pickups
                                   SET status = 'transferred',
                                       transfer_id = $transfer_id,
                                       updated_at = NOW()
                                   WHERE id IN ($ids_string)");

    if (!$update_pickup) {
        throw new Exception("Gagal update pickup: " . $conn->error);
    }

    echo "✅ Updated <span class='success'>$total_pickups pickup</span> jadi 'transferred'\n";

    // STEP 4: Update handover status
    echo "\n<h3>STEP 4: Update Status Handover → 'transferred'</h3>";

    $handovers = $conn->query("SELECT id, pickup_ids FROM handovers WHERE status IN ('validated', 'pending_validation')");
    $handover_updated = 0;

    while ($h = $handovers->fetch_assoc()) {
        $h_pickup_ids = json_decode($h['pickup_ids'], true);

        if (empty($h_pickup_ids)) continue;

        $h_ids_str = implode(',', array_map('intval', $h_pickup_ids));

        // Cek apakah semua pickup sudah transferred
        $check = $conn->query("SELECT COUNT(*) as total,
                                     SUM(CASE WHEN status = 'transferred' THEN 1 ELSE 0 END) as transferred
                              FROM pickups
                              WHERE id IN ($h_ids_str)")->fetch_assoc();

        if ($check['total'] == $check['transferred'] && $check['transferred'] > 0) {
            $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = {$h['id']}");
            echo "✅ Handover #{$h['id']}: 'validated' → 'transferred'\n";
            $handover_updated++;
        }
    }

    echo "\n<span class='success'>Total handover updated: $handover_updated</span>\n";

    $conn->commit();

    // SUCCESS
    echo "\n";
    echo "═══════════════════════════════════════════════\n";
    echo "<span class='success'>🎉 FORCE TRANSFER BERHASIL!</span>\n";
    echo "═══════════════════════════════════════════════\n";
    echo "\n";
    echo "✅ Transfer ID: #$transfer_id\n";
    echo "✅ Pickup ditransfer: $total_pickups\n";
    echo "✅ Total amount: Rp " . number_format($total_amount, 0, ',', '.') . "\n";
    echo "✅ Handover updated: $handover_updated\n";
    echo "\n";
    echo "📌 <span class='info'>Silakan refresh halaman transfer untuk melihat hasilnya</span>\n";
    echo "═══════════════════════════════════════════════\n";

} catch (Exception $e) {
    $conn->rollback();
    echo "\n<span class='error'>❌ ERROR: " . $e->getMessage() . "</span>\n";
}

echo "</pre>";

echo "<br><a href='transfer.php' class='btn btn-secondary'>💸 Buka Halaman Transfer</a>";
echo "<a href='dashboard.php' class='btn btn-secondary'>🏠 Dashboard</a>";
?>
