<?php
/**
 * FIX MANUAL: Update status handover berdasarkan status pickup
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🔧 Fix Handover Status Secara Manual</h2>";
echo "<pre>";

// Ambil semua handover yang status validated
$query = "SELECT id, pickup_ids, status FROM handovers WHERE status = 'validated' ORDER BY id DESC";
$result = $conn->query($query);

$fixed = [];
$skipped = [];

while ($handover = $result->fetch_assoc()) {
    $handover_id = $handover['id'];
    $pickup_ids = json_decode($handover['pickup_ids'], true);

    if (!is_array($pickup_ids) || empty($pickup_ids)) {
        $skipped[] = "Handover #$handover_id: pickup_ids kosong";
        continue;
    }

    $ids_str = implode(',', array_map('intval', $pickup_ids));

    // Cek status semua pickup di handover ini
    $check = $conn->query("SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN status = 'transferred' THEN 1 ELSE 0 END) as transferred,
                            SUM(CASE WHEN status != 'transferred' THEN 1 ELSE 0 END) as not_transferred
                           FROM pickups WHERE id IN ($ids_str)");
    $stats = $check->fetch_assoc();

    echo "\nHandover #$handover_id:\n";
    echo "  Total pickup: {$stats['total']}\n";
    echo "  Transferred: {$stats['transferred']}\n";
    echo "  Not transferred: {$stats['not_transferred']}\n";

    // Jika semua pickup sudah transferred, update handover
    if ($stats['not_transferred'] == 0 && $stats['total'] > 0) {
        $update = $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = $handover_id");
        if ($update) {
            echo "  ✅ Status diupdate ke 'transferred'\n";
            $fixed[] = $handover_id;
        } else {
            echo "  ❌ Gagal update: " . $conn->error . "\n";
        }
    } else {
        echo "  ⏭️  Skip (masih ada pickup belum transferred)\n";
        $skipped[] = "Handover #$handover_id";
    }
}

echo "\n\n===== RINGKASAN =====\n";
echo "✅ Fixed: " . count($fixed) . " handover\n";
if (!empty($fixed)) {
    echo "   IDs: " . implode(', ', $fixed) . "\n";
}
echo "⏭️  Skipped: " . count($skipped) . " handover\n";

echo "\n\n===== CEK DATA TERBARU =====\n";

// Tampilkan handover validated yang masih ada
$check_validated = $conn->query("SELECT id, status, pickup_ids FROM handovers WHERE status = 'validated' ORDER BY id DESC LIMIT 5");
echo "Handover dengan status 'validated':\n";
while ($h = $check_validated->fetch_assoc()) {
    $pickup_count = count(json_decode($h['pickup_ids'], true) ?? []);
    echo "  - Handover #{$h['id']}: {$pickup_count} pickup\n";
}

echo "\n</pre>";
echo '<br><a href="dashboard.php" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; display: inline-block;">← Kembali ke Dashboard</a>';
?>
