<?php
/**
 * FILE: admin/investigate-update-issue.php
 * FUNGSI: Investigasi kenapa UPDATE status pickup gagal
 */

require_once '../config.php';
check_login();
check_role('admin');

echo "<h2>Investigasi Masalah UPDATE Status Pickup</h2>";
echo "<style>
    body { font-family: monospace; padding: 20px; background: #f5f5f5; }
    pre { background: white; padding: 15px; border-radius: 5px; border: 1px solid #ddd; }
    .error { color: red; font-weight: bold; }
    .success { color: green; font-weight: bold; }
    .warning { color: orange; font-weight: bold; }
    h3 { margin-top: 20px; border-bottom: 2px solid #333; padding-bottom: 5px; }
    table { border-collapse: collapse; width: 100%; margin: 10px 0; background: white; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background: #333; color: white; }
</style>";

echo "<pre>";

// 1. CEK STRUKTUR TABEL PICKUPS
echo "<h3>1. Struktur Tabel 'pickups' - Kolom 'status'</h3>";
$describe = $conn->query("DESCRIBE pickups");
while ($col = $describe->fetch_assoc()) {
    if ($col['Field'] == 'status') {
        echo "Field: " . $col['Field'] . "\n";
        echo "Type: " . $col['Type'] . "\n";
        echo "Null: " . $col['Null'] . "\n";
        echo "Default: " . ($col['Default'] ?? 'NULL') . "\n";
        echo "Extra: " . ($col['Extra'] ?? '') . "\n";
    }
}

// 2. TEST UPDATE MANUAL
echo "\n<h3>2. Test UPDATE Manual pada 1 Pickup</h3>";

// Cari 1 pickup dengan status 'validated'
$test_pickup = $conn->query("SELECT id, status, transfer_id FROM pickups WHERE status = 'validated' LIMIT 1")->fetch_assoc();

if ($test_pickup) {
    $test_id = $test_pickup['id'];
    echo "Testing pada Pickup #$test_id (current status: '{$test_pickup['status']}')\n\n";

    // Coba update
    echo "Query: UPDATE pickups SET status = 'transferred' WHERE id = $test_id\n";
    $update_result = $conn->query("UPDATE pickups SET status = 'transferred' WHERE id = $test_id");

    if ($update_result) {
        echo "<span class='success'>✓ UPDATE berhasil!</span>\n";
        echo "Affected rows: " . $conn->affected_rows . "\n";

        // Cek hasilnya
        $after = $conn->query("SELECT status FROM pickups WHERE id = $test_id")->fetch_assoc();
        echo "Status setelah update: '" . $after['status'] . "'\n";

        if ($after['status'] == 'transferred') {
            echo "<span class='success'>✓ Status berhasil berubah!</span>\n";
        } else {
            echo "<span class='error'>✗ Status TIDAK berubah! Masih: '{$after['status']}'</span>\n";
        }

        // Rollback
        $conn->query("UPDATE pickups SET status = 'validated' WHERE id = $test_id");
        echo "\n(Test selesai, status dikembalikan ke 'validated')\n";
    } else {
        echo "<span class='error'>✗ UPDATE GAGAL!</span>\n";
        echo "Error: " . $conn->error . "\n";
    }
} else {
    echo "<span class='warning'>Tidak ada pickup 'validated' untuk test</span>\n";
}

// 3. CEK TRIGGERS
echo "\n<h3>3. Cek Triggers pada Tabel 'pickups'</h3>";
$triggers = $conn->query("SHOW TRIGGERS WHERE `Table` = 'pickups'");
if ($triggers && $triggers->num_rows > 0) {
    echo "<span class='warning'>DITEMUKAN TRIGGER!</span>\n\n";
    echo "<table>";
    echo "<tr><th>Trigger</th><th>Event</th><th>Timing</th><th>Statement</th></tr>";
    while ($t = $triggers->fetch_assoc()) {
        echo "<tr>";
        echo "<td>" . $t['Trigger'] . "</td>";
        echo "<td>" . $t['Event'] . "</td>";
        echo "<td>" . $t['Timing'] . "</td>";
        echo "<td><pre>" . htmlspecialchars($t['Statement']) . "</pre></td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<span class='success'>✓ Tidak ada trigger</span>\n";
}

// 4. CEK FOREIGN KEYS
echo "\n<h3>4. Cek Foreign Key Constraints</h3>";
$fks = $conn->query("SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                     FROM information_schema.KEY_COLUMN_USAGE
                     WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'pickups'
                     AND REFERENCED_TABLE_NAME IS NOT NULL");

if ($fks && $fks->num_rows > 0) {
    echo "<table>";
    echo "<tr><th>Constraint</th><th>Column</th><th>References</th></tr>";
    while ($fk = $fks->fetch_assoc()) {
        echo "<tr>";
        echo "<td>" . $fk['CONSTRAINT_NAME'] . "</td>";
        echo "<td>" . $fk['COLUMN_NAME'] . "</td>";
        echo "<td>" . $fk['REFERENCED_TABLE_NAME'] . "." . $fk['REFERENCED_COLUMN_NAME'] . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "<span class='success'>✓ Tidak ada foreign key constraint</span>\n";
}

// 5. CEK ENUM VALUES (jika status adalah ENUM)
echo "\n<h3>5. Cek Nilai ENUM untuk Kolom 'status' (jika ada)</h3>";
$column_type = $conn->query("SELECT COLUMN_TYPE FROM information_schema.COLUMNS
                             WHERE TABLE_SCHEMA = DATABASE()
                             AND TABLE_NAME = 'pickups'
                             AND COLUMN_NAME = 'status'")->fetch_assoc();

if ($column_type) {
    $type = $column_type['COLUMN_TYPE'];
    echo "Column Type: $type\n";

    if (stripos($type, 'enum') !== false) {
        echo "\n<span class='warning'>Status adalah ENUM field!</span>\n";
        echo "Allowed values: $type\n\n";

        // Cek apakah 'transferred' ada di enum
        if (stripos($type, 'transferred') !== false) {
            echo "<span class='success'>✓ 'transferred' ada dalam enum values</span>\n";
        } else {
            echo "<span class='error'>✗ 'transferred' TIDAK ADA dalam enum values!</span>\n";
            echo "<span class='error'>INI MASALAHNYA! Anda perlu ALTER TABLE untuk menambahkan 'transferred'</span>\n";
        }
    } else {
        echo "<span class='success'>✓ Status bukan ENUM (VARCHAR/TEXT)</span>\n";
    }
}

echo "</pre>";

echo "<br><a href='dashboard.php' style='padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;'>Kembali ke Dashboard</a>";
?>
