<?php
/**
 * FILE: admin/cleanup-transferred-pickups.php
 * FUNGSI: Cleanup semua pickup yang sudah ditransfer tapi status masih 'validated'
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🧹 Cleanup: Fix Status Pickup yang Sudah Ditransfer</h2>";
echo "<style>
    body { font-family: monospace; padding: 20px; background: #f0f2f5; }
    pre { background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd; line-height: 1.6; }
    .error { color: #dc2626; font-weight: bold; }
    .success { color: #16a34a; font-weight: bold; }
    .warning { color: #ea580c; font-weight: bold; }
    .info { color: #2563eb; font-weight: bold; }
    h3 { margin-top: 25px; border-bottom: 3px solid #4f46e5; padding-bottom: 8px; color: #4f46e5; }
    table { border-collapse: collapse; width: 100%; margin: 15px 0; background: white; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }
    th { background: #4f46e5; color: white; }
</style>";

echo "<pre>";

// STEP 1: Tampilkan pickup yang statusnya 'validated' dan tampil di halaman transfer
echo "<h3>STEP 1: Identifikasi Pickup yang Tampil di Halaman Transfer</h3>";

$pickups_in_transfer_page = $conn->query("SELECT p.id, p.outlet_id, p.status, p.transfer_id,
                                                  p.amount_taken, p.actual_amount_received,
                                                  o.outlet_name
                                          FROM pickups p
                                          JOIN outlets o ON p.outlet_id = o.id
                                          WHERE p.status = 'validated'
                                          ORDER BY p.id ASC");

$total_count = $pickups_in_transfer_page->num_rows;
echo "Ditemukan: <span class='warning'>$total_count pickup</span> dengan status 'validated'\n\n";

// Pisahkan yang punya transfer_id vs yang tidak
$with_transfer_id = [];
$without_transfer_id = [];

while ($p = $pickups_in_transfer_page->fetch_assoc()) {
    if ($p['transfer_id']) {
        $with_transfer_id[] = $p;
    } else {
        $without_transfer_id[] = $p;
    }
}

$count_with = count($with_transfer_id);
$count_without = count($without_transfer_id);

echo "├─ <span class='error'>Dengan transfer_id (ANOMALI): $count_with pickup</span>\n";
echo "│  → Ini sudah ditransfer, tapi status masih 'validated'\n";
echo "│  → <span class='warning'>INI YANG BIKIN MUNCUL DI HALAMAN TRANSFER!</span>\n";
echo "│\n";
echo "└─ <span class='success'>Tanpa transfer_id (NORMAL): $count_without pickup</span>\n";
echo "   → Ini memang belum ditransfer, boleh tampil di halaman transfer\n";

// STEP 2: Tampilkan detail pickup yang bermasalah
if ($count_with > 0) {
    echo "\n<h3>STEP 2: Detail Pickup yang Sudah Ditransfer (Tapi Status Masih 'validated')</h3>";

    echo "<table>";
    echo "<tr><th>Pickup ID</th><th>Outlet</th><th>Status</th><th>Transfer ID</th><th>Amount</th></tr>";

    foreach ($with_transfer_id as $p) {
        echo "<tr>";
        echo "<td>#" . $p['id'] . "</td>";
        echo "<td>" . $p['outlet_name'] . "</td>";
        echo "<td><span class='warning'>" . $p['status'] . "</span></td>";
        echo "<td><span class='error'>#" . $p['transfer_id'] . "</span></td>";
        $amount = $p['actual_amount_received'] ?? $p['amount_taken'];
        echo "<td>Rp " . number_format($amount, 0, ',', '.') . "</td>";
        echo "</tr>";
    }

    echo "</table>";

    // STEP 3: FIX - Update status jadi 'transferred'
    echo "\n<h3>STEP 3: Fix Status → 'transferred'</h3>";

    $fixed_count = 0;
    $error_count = 0;

    foreach ($with_transfer_id as $p) {
        $pickup_id = $p['id'];
        $transfer_id = $p['transfer_id'];

        $update = $conn->query("UPDATE pickups
                               SET status = 'transferred', updated_at = NOW()
                               WHERE id = $pickup_id");

        if ($update) {
            echo "✅ Pickup #$pickup_id: 'validated' → 'transferred' (Transfer #$transfer_id)\n";
            $fixed_count++;
        } else {
            echo "❌ Pickup #$pickup_id: GAGAL - " . $conn->error . "\n";
            $error_count++;
        }
    }

    echo "\n<span class='success'>✅ Berhasil diperbaiki: $fixed_count pickup</span>\n";
    if ($error_count > 0) {
        echo "<span class='error'>❌ Gagal: $error_count pickup</span>\n";
    }

    // STEP 4: Update handover yang seharusnya 'transferred'
    echo "\n<h3>STEP 4: Update Handover Status</h3>";

    $handovers = $conn->query("SELECT id, pickup_ids, status
                              FROM handovers
                              WHERE status = 'validated'");

    $handover_fixed = 0;
    while ($h = $handovers->fetch_assoc()) {
        $pickup_ids = json_decode($h['pickup_ids'], true);

        if (empty($pickup_ids)) continue;

        $ids_str = implode(',', array_map('intval', $pickup_ids));

        // Cek apakah semua pickup sudah transferred
        $check = $conn->query("SELECT COUNT(*) as total,
                                     SUM(CASE WHEN status = 'transferred' THEN 1 ELSE 0 END) as transferred
                              FROM pickups
                              WHERE id IN ($ids_str)")->fetch_assoc();

        if ($check['total'] == $check['transferred'] && $check['transferred'] > 0) {
            $update_h = $conn->query("UPDATE handovers
                                     SET status = 'transferred', updated_at = NOW()
                                     WHERE id = {$h['id']}");
            if ($update_h) {
                echo "✅ Handover #{$h['id']}: 'validated' → 'transferred'\n";
                $handover_fixed++;
            }
        }
    }

    echo "\n<span class='success'>✅ Handover diupdate: $handover_fixed</span>\n";

} else {
    echo "\n<span class='success'>✅ Tidak ada pickup anomali yang perlu diperbaiki!</span>\n";
}

// STEP 5: Verifikasi hasil
echo "\n<h3>STEP 5: Verifikasi - Cek Halaman Transfer Sekarang</h3>";

$after_cleanup = $conn->query("SELECT COUNT(*) as count,
                                     COALESCE(SUM(COALESCE(actual_amount_received, amount_taken)), 0) as total
                              FROM pickups
                              WHERE status = 'validated'
                              AND transfer_id IS NULL")->fetch_assoc();

echo "Pickup yang tampil di halaman transfer sekarang:\n";
echo "├─ Jumlah: <span class='info'>" . $after_cleanup['count'] . " pickup</span>\n";
echo "└─ Total: <span class='info'>Rp " . number_format($after_cleanup['total'], 0, ',', '.') . "</span>\n";

// SUMMARY
echo "\n";
echo "═══════════════════════════════════════════════\n";
echo "<span class='success'>🎉 CLEANUP SELESAI!</span>\n";
echo "═══════════════════════════════════════════════\n";
echo "\n";
if (isset($fixed_count)) {
    echo "✅ Pickup diperbaiki: $fixed_count\n";
    echo "✅ Handover diupdate: $handover_fixed\n";
}
echo "✅ Pickup tersisa di transfer: " . $after_cleanup['count'] . "\n";
echo "\n";
echo "📌 <span class='info'>Silakan refresh halaman transfer untuk melihat hasilnya</span>\n";
echo "═══════════════════════════════════════════════\n";

echo "</pre>";

echo "<br><a href='transfer.php' style='padding: 12px 24px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block;'>💸 Refresh Halaman Transfer</a>";
echo " ";
echo "<a href='dashboard.php' style='padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block; margin-left: 10px;'>🏠 Kembali ke Dashboard</a>";
?>
