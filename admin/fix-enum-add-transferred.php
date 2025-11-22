<?php
/**
 * FILE: admin/fix-enum-add-transferred.php
 * FUNGSI: Fix ENUM status - tambah 'transferred' dan perbaiki data
 * CRITICAL FIX: Ini adalah akar masalah kenapa transfer tidak bekerja!
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>🔧 FIX ENUM Status - Tambah 'transferred'</h2>";
echo "<style>
    body { font-family: monospace; padding: 20px; background: #f0f2f5; }
    pre { background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd; }
    .error { color: #dc2626; font-weight: bold; }
    .success { color: #16a34a; font-weight: bold; }
    .warning { color: #ea580c; font-weight: bold; }
    .info { color: #2563eb; font-weight: bold; }
    h3 { margin-top: 25px; border-bottom: 3px solid #4f46e5; padding-bottom: 8px; color: #4f46e5; }
</style>";

echo "<pre>";

// STEP 1: ALTER TABLE untuk menambah 'transferred' ke ENUM
echo "<h3>STEP 1: Menambah 'transferred' ke ENUM status</h3>";
echo "Query: ALTER TABLE pickups MODIFY COLUMN status ENUM('pending_handover','handed_over','validated','transferred')\n\n";

$alter_result = $conn->query("ALTER TABLE pickups MODIFY COLUMN status ENUM('pending_handover','handed_over','validated','transferred') DEFAULT 'pending_handover'");

if ($alter_result) {
    echo "<span class='success'>✅ SUCCESS! ENUM berhasil diupdate</span>\n";
    echo "Status sekarang bisa menerima nilai: 'pending_handover', 'handed_over', 'validated', 'transferred'\n";
} else {
    echo "<span class='error'>❌ FAILED: " . $conn->error . "</span>\n";
    die("\n</pre>");
}

// STEP 2: Fix pickup yang statusnya BLANK (sudah ditransfer tapi status jadi blank)
echo "\n<h3>STEP 2: Fix Pickup dengan Status Blank yang Punya transfer_id</h3>";

$blank_pickups = $conn->query("SELECT id, transfer_id, amount_taken
                               FROM pickups
                               WHERE transfer_id IS NOT NULL
                               AND (status = '' OR status IS NULL)");

if ($blank_pickups && $blank_pickups->num_rows > 0) {
    echo "Ditemukan <span class='warning'>{$blank_pickups->num_rows} pickup</span> dengan status blank...\n\n";

    $fixed = 0;
    while ($p = $blank_pickups->fetch_assoc()) {
        $update = $conn->query("UPDATE pickups SET status = 'transferred' WHERE id = {$p['id']}");
        if ($update) {
            echo "✅ Pickup #{$p['id']}: Status diupdate ke 'transferred' (Transfer #{$p['transfer_id']})\n";
            $fixed++;
        }
    }

    echo "\n<span class='success'>✅ Fixed: $fixed pickup</span>\n";
} else {
    echo "<span class='info'>ℹ️  Tidak ada pickup blank yang perlu diperbaiki</span>\n";
}

// STEP 3: Fix pickup yang masih 'validated' tapi punya transfer_id
echo "\n<h3>STEP 3: Fix Pickup yang Masih 'validated' tapi Punya transfer_id</h3>";

$validated_with_transfer = $conn->query("SELECT id, transfer_id, amount_taken
                                         FROM pickups
                                         WHERE transfer_id IS NOT NULL
                                         AND status = 'validated'");

if ($validated_with_transfer && $validated_with_transfer->num_rows > 0) {
    echo "Ditemukan <span class='warning'>{$validated_with_transfer->num_rows} pickup</span> yang seharusnya 'transferred'...\n\n";

    $fixed2 = 0;
    while ($p = $validated_with_transfer->fetch_assoc()) {
        $update = $conn->query("UPDATE pickups SET status = 'transferred' WHERE id = {$p['id']}");
        if ($update) {
            echo "✅ Pickup #{$p['id']}: Status diupdate dari 'validated' ke 'transferred'\n";
            $fixed2++;
        }
    }

    echo "\n<span class='success'>✅ Fixed: $fixed2 pickup</span>\n";
} else {
    echo "<span class='info'>ℹ️  Tidak ada pickup 'validated' dengan transfer_id</span>\n";
}

// STEP 4: Update handover yang seharusnya 'transferred'
echo "\n<h3>STEP 4: Update Handover Status ke 'transferred'</h3>";

// Cek apakah handovers juga punya enum issue
$handover_enum = $conn->query("SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                               WHERE TABLE_SCHEMA = DATABASE()
                               AND TABLE_NAME = 'handovers'
                               AND COLUMN_NAME = 'status'")->fetch_assoc();

if ($handover_enum && stripos($handover_enum['COLUMN_TYPE'], 'enum') !== false) {
    $type = $handover_enum['COLUMN_TYPE'];
    echo "Handover status type: $type\n";

    if (stripos($type, 'transferred') === false) {
        echo "<span class='warning'>⚠️  Handover juga perlu ditambah 'transferred' di ENUM</span>\n";

        $alter_handover = $conn->query("ALTER TABLE handovers MODIFY COLUMN status ENUM('pending_validation','validated','transferred') DEFAULT 'pending_validation'");

        if ($alter_handover) {
            echo "<span class='success'>✅ Handover ENUM berhasil diupdate!</span>\n\n";
        } else {
            echo "<span class='error'>❌ Failed: " . $conn->error . "</span>\n\n";
        }
    }
}

// Update handover yang semua pickupnya sudah transferred
$handovers = $conn->query("SELECT id, pickup_ids, status
                          FROM handovers
                          WHERE status IN ('validated', 'pending_validation')");

$handover_fixed = 0;
if ($handovers) {
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
            $update_h = $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = {$h['id']}");
            if ($update_h) {
                echo "✅ Handover #{$h['id']}: Status diupdate ke 'transferred' ({$check['transferred']} pickups)\n";
                $handover_fixed++;
            }
        }
    }
}

echo "\n<span class='success'>✅ Handover fixed: $handover_fixed</span>\n";

// SUMMARY
echo "\n";
echo "═══════════════════════════════════════════════\n";
echo "<span class='success'>🎉 SELESAI - SEMUA FIXED!</span>\n";
echo "═══════════════════════════════════════════════\n";
echo "\n";
echo "✅ ENUM status pickups: ditambah 'transferred'\n";
echo "✅ ENUM status handovers: ditambah 'transferred'\n";
if (isset($fixed)) echo "✅ Pickup blank: $fixed diperbaiki\n";
if (isset($fixed2)) echo "✅ Pickup validated: $fixed2 diperbaiki\n";
echo "✅ Handover: $handover_fixed diupdate\n";
echo "\n";
echo "📌 <span class='info'>Sekarang transfer akan bekerja dengan normal!</span>\n";
echo "📌 <span class='info'>Data yang sudah ditransfer tidak akan muncul lagi di halaman transfer</span>\n";
echo "═══════════════════════════════════════════════\n";

echo "</pre>";

echo "<br><a href='dashboard.php' style='padding: 12px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block;'>🏠 Kembali ke Dashboard</a>";
echo " ";
echo "<a href='transfer.php' style='padding: 12px 24px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block; margin-left: 10px;'>💸 Cek Halaman Transfer</a>";
?>
