<?php
/**
 * FILE: admin/fix-blank-status.php
 * FUNGSI: Fix pickup yang punya transfer_id tapi status blank/bukan 'transferred'
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>Memperbaiki Pickup dengan Status Anomali</h2>";
echo "<pre>";

// Fix: Pickup yang punya transfer_id tapi status BUKAN 'transferred'
$query = "SELECT id, outlet_id, status, transfer_id, amount_taken
          FROM pickups
          WHERE transfer_id IS NOT NULL
          AND (status != 'transferred' OR status IS NULL OR status = '')";

$result = $conn->query($query);

if ($result->num_rows == 0) {
    echo "✅ Tidak ada pickup anomali yang perlu diperbaiki!\n";
} else {
    echo "Ditemukan " . $result->num_rows . " pickup dengan status anomali...\n\n";

    $fixed_count = 0;
    $error_count = 0;

    while ($pickup = $result->fetch_assoc()) {
        $pickup_id = $pickup['id'];
        $transfer_id = $pickup['transfer_id'];
        $current_status = $pickup['status'] ?? 'NULL';

        // Update status jadi 'transferred'
        $update_stmt = $conn->prepare("UPDATE pickups
                                       SET status = 'transferred',
                                           updated_at = NOW()
                                       WHERE id = ?");
        $update_stmt->bind_param("i", $pickup_id);

        if ($update_stmt->execute()) {
            echo "✅ Pickup #$pickup_id: Status diupdate dari '$current_status' ke 'transferred' (Transfer #$transfer_id)\n";
            $fixed_count++;
        } else {
            echo "❌ Pickup #$pickup_id: GAGAL - " . $update_stmt->error . "\n";
            $error_count++;
        }
    }

    echo "\n";
    echo "======================================\n";
    echo "SELESAI!\n";
    echo "✅ Berhasil diperbaiki: $fixed_count\n";
    if ($error_count > 0) {
        echo "❌ Error: $error_count\n";
    }
    echo "======================================\n";

    // Sekarang update handover yang seharusnya 'transferred'
    if ($fixed_count > 0) {
        echo "\n<h3>Updating Handover Status...</h3>\n";

        $handovers = $conn->query("SELECT id, pickup_ids, status
                                  FROM handovers
                                  WHERE status = 'validated'");

        $handover_fixed = 0;
        while ($handover = $handovers->fetch_assoc()) {
            $handover_id = $handover['id'];
            $pickup_ids = json_decode($handover['pickup_ids'], true);

            if (empty($pickup_ids)) continue;

            $ids_string = implode(',', array_map('intval', $pickup_ids));

            // Cek apakah semua pickup sudah transferred
            $check_query = "SELECT COUNT(*) as total,
                                  SUM(CASE WHEN status = 'transferred' THEN 1 ELSE 0 END) as transferred
                           FROM pickups
                           WHERE id IN ($ids_string)";

            $check_result = $conn->query($check_query);
            $check = $check_result->fetch_assoc();

            if ($check['total'] == $check['transferred'] && $check['transferred'] > 0) {
                $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = $handover_id");
                echo "✅ Handover #$handover_id: Status diupdate ke 'transferred'\n";
                $handover_fixed++;
            }
        }

        echo "\n✅ Handover yang diupdate: $handover_fixed\n";
    }
}

echo "</pre>";

echo "<br><a href='dashboard.php' style='padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;'>Kembali ke Dashboard</a>";
?>
