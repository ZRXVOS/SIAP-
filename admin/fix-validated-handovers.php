<?php
/**
 * FILE: admin/fix-validated-handovers.php
 * FUNGSI: Fix validated handovers yang belum punya actual_amount_received dan difference
 * JALANKAN SEKALI SAJA untuk memperbaiki data historical
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>Memperbaiki Data Handovers yang Sudah Tervalidasi</h2>";
echo "<pre>";

// Get semua handovers dengan status 'validated' yang belum punya actual_amount_received
$query = "SELECT id, pickup_ids, total_amount, actual_amount_received, difference
          FROM handovers
          WHERE status = 'validated'
          AND (actual_amount_received IS NULL OR actual_amount_received = 0 OR difference IS NULL)";

$result = $conn->query($query);

if ($result->num_rows == 0) {
    echo "✅ Tidak ada data yang perlu diperbaiki!\n";
    exit;
}

echo "Ditemukan " . $result->num_rows . " handover yang perlu diperbaiki...\n\n";

$fixed_count = 0;
$error_count = 0;

while ($handover = $result->fetch_assoc()) {
    $handover_id = $handover['id'];
    $pickup_ids = json_decode($handover['pickup_ids'], true);

    if (empty($pickup_ids)) {
        echo "⚠️  Handover #$handover_id: pickup_ids kosong, dilewati\n";
        $error_count++;
        continue;
    }

    $ids_string = implode(',', array_map('intval', $pickup_ids));

    // Hitung total actual_amount_received dari pickups
    $totals_query = "SELECT
                        COALESCE(SUM(actual_amount_received), 0) as total_actual,
                        COALESCE(SUM(amount_taken), 0) as total_reported
                     FROM pickups
                     WHERE id IN ($ids_string)";

    $totals_result = $conn->query($totals_query);
    $totals = $totals_result->fetch_assoc();

    $total_actual = $totals['total_actual'];
    $total_reported = $totals['total_reported'];
    $calculated_difference = $total_actual - $total_reported;

    // Update handover
    $update_stmt = $conn->prepare("UPDATE handovers
                                   SET actual_amount_received = ?,
                                       difference = ?
                                   WHERE id = ?");
    $update_stmt->bind_param("ddi", $total_actual, $calculated_difference, $handover_id);

    if ($update_stmt->execute()) {
        echo "✅ Handover #$handover_id: ";
        echo "Total Dilaporkan = " . format_rupiah($total_reported) . ", ";
        echo "Aktual Diterima = " . format_rupiah($total_actual) . ", ";
        echo "Selisih = " . format_rupiah($calculated_difference) . "\n";
        $fixed_count++;
    } else {
        echo "❌ Handover #$handover_id: GAGAL - " . $update_stmt->error . "\n";
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
echo "</pre>";

echo "<br><a href='dashboard.php' style='padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px;'>Kembali ke Dashboard</a>";
?>
