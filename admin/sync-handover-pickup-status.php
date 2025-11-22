<?php
/**
 * SYNC: Sinkronisasi status handover dengan pickup
 * Memastikan konsistensi data antara handover dan pickup
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🔄 Sinkronisasi Status Handover & Pickup</h2>";
echo "<pre>";

$conn->begin_transaction();

try {
    $issues_fixed = 0;

    echo "===== STEP 1: FIX HANDOVER STATUS BERDASARKAN PICKUP =====\n\n";

    // Ambil semua handover yang statusnya validated
    $query_handovers = "SELECT id, pickup_ids, status FROM handovers WHERE status = 'validated'";
    $result = $conn->query($query_handovers);

    while ($handover = $result->fetch_assoc()) {
        $handover_id = $handover['id'];
        $pickup_ids = json_decode($handover['pickup_ids'], true);

        if (!is_array($pickup_ids) || empty($pickup_ids)) {
            continue;
        }

        $ids_str = implode(',', array_map('intval', $pickup_ids));

        // Cek status semua pickup
        $check = $conn->query("SELECT COUNT(*) as not_transferred
                              FROM pickups
                              WHERE id IN ($ids_str) AND status != 'transferred'");
        $stat = $check->fetch_assoc();

        // Jika semua pickup sudah transferred, update handover
        if ($stat['not_transferred'] == 0) {
            $update = $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = $handover_id");
            if ($update) {
                echo "✅ Handover #$handover_id: validated → transferred\n";
                $issues_fixed++;
            }
        }
    }

    echo "\n===== STEP 2: FIX PICKUP STATUS YANG INKONSISTEN =====\n\n";

    // Cari pickup yang ada di handover dengan status transferred, tapi pickup belum transferred
    $query_inconsistent = "SELECT DISTINCT h.id as handover_id, h.pickup_ids, h.status
                          FROM handovers h
                          WHERE h.status = 'transferred'";
    $result_inc = $conn->query($query_inconsistent);

    while ($handover = $result_inc->fetch_assoc()) {
        $handover_id = $handover['handover_id'];
        $pickup_ids = json_decode($handover['pickup_ids'], true);

        if (!is_array($pickup_ids) || empty($pickup_ids)) {
            continue;
        }

        foreach ($pickup_ids as $pid) {
            // Cek status pickup ini
            $check_pickup = $conn->query("SELECT id, status, transfer_id FROM pickups WHERE id = $pid");
            if ($check_pickup && $check_pickup->num_rows > 0) {
                $pickup = $check_pickup->fetch_assoc();

                // Jika pickup belum transferred padahal handovernya sudah transferred
                if ($pickup['status'] != 'transferred') {
                    echo "⚠️  Pickup #{$pid} status '{$pickup['status']}' tapi handover #{$handover_id} sudah 'transferred'\n";
                    echo "   → Akan diset ke 'validated' agar bisa ditransfer ulang\n";

                    // Set pickup ke validated agar bisa ditransfer
                    $fix = $conn->query("UPDATE pickups SET status = 'validated', updated_at = NOW() WHERE id = $pid");
                    if ($fix) {
                        echo "   ✅ Fixed!\n";
                        $issues_fixed++;
                    }

                    // Dan set handover kembali ke validated karena ada pickup yang belum transferred
                    $fix_handover = $conn->query("UPDATE handovers SET status = 'validated', updated_at = NOW() WHERE id = $handover_id");
                    if ($fix_handover) {
                        echo "   ✅ Handover #{$handover_id} dikembalikan ke 'validated'\n";
                    }
                }
            }
        }
    }

    $conn->commit();

    echo "\n\n===== SELESAI =====\n";
    echo "Total issues fixed: $issues_fixed\n";
    echo "\nSilakan refresh dashboard untuk melihat perubahan.\n";

} catch (Exception $e) {
    $conn->rollback();
    echo "❌ ERROR: " . $e->getMessage() . "\n";
}

echo "</pre>";
echo '<br><a href="dashboard.php" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; display: inline-block;">← Kembali ke Dashboard</a>';
?>
