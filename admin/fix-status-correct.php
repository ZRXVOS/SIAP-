<?php
/**
 * FIX CORRECT: Perbaiki status yang benar
 * Logic yang BENAR:
 * 1. Cari handover yang SEMUA pickupnya sudah transferred -> update handover ke transferred
 * 2. Cari handover yang ADA pickup belum transferred -> handover tetap validated
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>✅ Fix Status Handover & Pickup (LOGIC BENAR)</h2>";
echo "<style>pre { font-family: monospace; font-size: 13px; }</style>";
echo "<pre>";

$conn->begin_transaction();

try {
    echo "===== ANALISA DATA =====\n\n";

    // Cek semua handover
    $query = "SELECT h.id, h.status, h.pickup_ids,
              (SELECT COUNT(*) FROM pickups p WHERE FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', ''))) as total_pickup,
              (SELECT COUNT(*) FROM pickups p WHERE FIND_IN_SET(p.id, REPLACE(REPLACE(REPLACE(h.pickup_ids, '[', ''), ']', ''), '\"', '')) AND p.status = 'transferred') as transferred_pickup
              FROM handovers h
              ORDER BY h.id DESC
              LIMIT 20";

    $result = $conn->query($query);

    echo "ID | Status Handover | Total Pickup | Transferred | Action\n";
    echo "---|-----------------|--------------|-------------|--------\n";

    $to_fix = [];

    while ($h = $result->fetch_assoc()) {
        $status_display = str_pad($h['status'], 15);
        $total = $h['total_pickup'];
        $transferred = $h['transferred_pickup'];

        // Logic yang BENAR:
        // Jika SEMUA pickup sudah transferred -> handover harus transferred
        // Jika MASIH ADA yang belum transferred -> handover harus validated

        $correct_status = ($transferred == $total && $total > 0) ? 'transferred' : 'validated';

        $action = '';
        if ($h['status'] != $correct_status) {
            $action = "FIX: {$h['status']} -> $correct_status";
            $to_fix[] = [
                'id' => $h['id'],
                'current' => $h['status'],
                'correct' => $correct_status
            ];
        } else {
            $action = "OK";
        }

        printf("#%-2d | %-15s | %12d | %11d | %s\n",
               $h['id'], $status_display, $total, $transferred, $action);
    }

    echo "\n\n===== PERBAIKAN =====\n\n";

    if (empty($to_fix)) {
        echo "✅ Semua status sudah benar! Tidak ada yang perlu diperbaiki.\n";
    } else {
        foreach ($to_fix as $fix) {
            $update = $conn->query("UPDATE handovers SET status = '{$fix['correct']}', updated_at = NOW() WHERE id = {$fix['id']}");
            if ($update) {
                echo "✅ Handover #{$fix['id']}: {$fix['current']} → {$fix['correct']}\n";
            } else {
                throw new Exception("Gagal update handover #{$fix['id']}: " . $conn->error);
            }
        }
    }

    $conn->commit();

    echo "\n\n===== SELESAI =====\n";
    echo "Total diperbaiki: " . count($to_fix) . " handover\n";
    echo "\n⚠️ PENTING: Setelah ini, HAPUS file sync-handover-pickup-status.php karena logic-nya SALAH!\n";
    echo "\nSilakan refresh dashboard untuk melihat hasil yang benar.\n";

} catch (Exception $e) {
    $conn->rollback();
    echo "\n❌ ERROR: " . $e->getMessage() . "\n";
}

echo "</pre>";
echo '<br><a href="dashboard.php" style="padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 20px;">← Kembali ke Dashboard</a>';
?>
