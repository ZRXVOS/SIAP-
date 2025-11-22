<?php
/**
 * FILE: admin/fix-transferred-handovers.php
 * FUNGSI: Fix handover status yang seharusnya 'transferred' tapi masih 'validated'
 * JALANKAN SEKALI SAJA untuk memperbaiki data historical
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>Memperbaiki Status Handovers yang Sudah Ditransfer</h2>";
echo "<pre>";

// Get semua handovers dengan status 'validated'
$query = "SELECT id, pickup_ids, status
          FROM handovers
          WHERE status = 'validated'";

$result = $conn->query($query);

if ($result->num_rows == 0) {
    echo "✅ Tidak ada handover 'validated' yang perlu diperiksa!\n";
    exit;
}

echo "Ditemukan " . $result->num_rows . " handover dengan status 'validated'...\n";
echo "Memeriksa apakah semua pickup sudah ditransfer...\n\n";

$fixed_count = 0;
$skip_count = 0;

while ($handover = $result->fetch_assoc()) {
    $handover_id = $handover['id'];
    $pickup_ids = json_decode($handover['pickup_ids'], true);

    if (empty($pickup_ids)) {
        echo "⚠️  Handover #$handover_id: pickup_ids kosong, dilewati\n";
        $skip_count++;
        continue;
    }

    $ids_string = implode(',', array_map('intval', $pickup_ids));

    // Cek apakah semua pickup sudah transferred
    $check_query = "SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'transferred' THEN 1 ELSE 0 END) as transferred
                    FROM pickups
                    WHERE id IN ($ids_string)";

    $check_result = $conn->query($check_query);
    $check = $check_result->fetch_assoc();

    $total_pickups = $check['total'];
    $transferred_pickups = $check['transferred'];

    if ($total_pickups == $transferred_pickups && $transferred_pickups > 0) {
        // Semua pickup sudah transferred, update status handover
        $update_stmt = $conn->prepare("UPDATE handovers
                                       SET status = 'transferred',
                                           updated_at = NOW()
                                       WHERE id = ?");
        $update_stmt->bind_param("i", $handover_id);

        if ($update_stmt->execute()) {
            echo "✅ Handover #$handover_id: Status diupdate ke 'transferred' ($transferred_pickups/$total_pickups pickup sudah ditransfer)\n";
            $fixed_count++;
        } else {
            echo "❌ Handover #$handover_id: GAGAL - " . $update_stmt->error . "\n";
        }
    } else {
        echo "⏭️  Handover #$handover_id: Masih ada pickup yang belum ditransfer ($transferred_pickups/$total_pickups), status tetap 'validated'\n";
        $skip_count++;
    }
}

echo "\n";
echo "======================================\n";
echo "SELESAI!\n";
echo "✅ Berhasil diupdate ke 'transferred': $fixed_count\n";
echo "⏭️  Dilewati (belum semua ditransfer): $skip_count\n";
echo "======================================\n";
echo "</pre>";

echo "<br><a href='dashboard.php' style='padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;'>Kembali ke Dashboard</a>";
?>
