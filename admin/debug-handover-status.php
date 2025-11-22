<?php
/**
 * DEBUG: Cek status handover #14 dan #15
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🔍 Debug Handover Status</h2>";
echo "<pre>";

// Cek handover #14 dan #15
$handover_ids = [14, 15];

foreach ($handover_ids as $hid) {
    echo "\n===== HANDOVER #$hid =====\n";

    // Get handover data
    $query = "SELECT * FROM handovers WHERE id = $hid";
    $result = $conn->query($query);

    if ($result->num_rows == 0) {
        echo "❌ Handover tidak ditemukan!\n";
        continue;
    }

    $handover = $result->fetch_assoc();
    echo "Status: " . $handover['status'] . "\n";
    echo "Pickup IDs: " . $handover['pickup_ids'] . "\n";

    // Decode pickup_ids
    $pickup_ids = json_decode($handover['pickup_ids'], true);

    if (!is_array($pickup_ids) || empty($pickup_ids)) {
        echo "⚠️ Pickup IDs kosong atau invalid\n";
        continue;
    }

    echo "Jumlah pickup: " . count($pickup_ids) . "\n";
    echo "Pickup IDs array: " . implode(', ', $pickup_ids) . "\n\n";

    // Cek status masing-masing pickup
    $ids_str = implode(',', array_map('intval', $pickup_ids));
    $pickup_query = "SELECT id, status, transfer_id FROM pickups WHERE id IN ($ids_str)";
    $pickup_result = $conn->query($pickup_query);

    echo "Detail Pickup:\n";
    $count_transferred = 0;
    $count_not_transferred = 0;

    while ($pickup = $pickup_result->fetch_assoc()) {
        echo "  - Pickup #{$pickup['id']}: status = {$pickup['status']}, transfer_id = {$pickup['transfer_id']}\n";
        if ($pickup['status'] == 'transferred') {
            $count_transferred++;
        } else {
            $count_not_transferred++;
        }
    }

    echo "\nRingkasan:\n";
    echo "  ✅ Sudah transferred: $count_transferred\n";
    echo "  ⏳ Belum transferred: $count_not_transferred\n";

    if ($count_not_transferred == 0) {
        echo "\n🎯 SEMUA PICKUP SUDAH TRANSFERRED - Handover seharusnya status 'transferred'\n";

        // Update status
        $update = $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = $hid");
        if ($update) {
            echo "✅ Status handover berhasil diupdate ke 'transferred'\n";
        } else {
            echo "❌ Gagal update status: " . $conn->error . "\n";
        }
    } else {
        echo "\n⚠️ Masih ada pickup yang belum transferred\n";
    }
}

echo "\n\n===== SELESAI =====\n";
echo "Silakan refresh halaman dashboard untuk melihat perubahan.\n";
echo "</pre>";

echo '<br><a href="dashboard.php" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;">← Kembali ke Dashboard</a>';
?>
