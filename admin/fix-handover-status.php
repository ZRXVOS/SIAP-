<?php
/**
 * FILE: admin/fix-handover-status.php
 * FUNGSI: One-time script untuk fix status handover yang sudah di-transfer
 * CATATAN: Jalankan sekali saja untuk fix data existing
 */

require_once '../config.php';
check_login();
check_role('admin');

$fixed_count = 0;
$errors = [];

$conn->begin_transaction();

try {
    // Cari handover dengan status 'validated'
    $query_handovers = "SELECT DISTINCT h.id, h.pickup_ids FROM handovers h WHERE h.status = 'validated'";
    $result_handovers = $conn->query($query_handovers);

    if ($result_handovers) {
        while ($handover = $result_handovers->fetch_assoc()) {
            $handover_pickup_ids = json_decode($handover['pickup_ids'], true) ?? [];

            if (!empty($handover_pickup_ids)) {
                $handover_ids_str = implode(',', array_map('intval', $handover_pickup_ids));

                // Cek apakah ada pickup yang belum transferred di handover ini
                $check_query = "SELECT COUNT(*) as c FROM pickups WHERE id IN ($handover_ids_str) AND status != 'transferred'";
                $check = $conn->query($check_query)->fetch_assoc();

                // Jika semua pickup sudah transferred, update status handover
                if ($check['c'] == 0) {
                    $conn->query("UPDATE handovers SET status = 'transferred', updated_at = NOW() WHERE id = " . $handover['id']);
                    $fixed_count++;
                }
            }
        }
    }

    $conn->commit();
    $success = "✅ Berhasil memperbaiki $fixed_count handover yang statusnya seharusnya 'transferred'";

} catch (Exception $e) {
    $conn->rollback();
    $error = "❌ Error: " . $e->getMessage();
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fix Handover Status</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f6fa;
            padding: 40px 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        h1 {
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
        }
        .message {
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 16px;
        }
        .success {
            background: #d1fae5;
            color: #065f46;
            border: 2px solid #10b981;
        }
        .error {
            background: #fee2e2;
            color: #991b1b;
            border: 2px solid #ef4444;
        }
        .btn {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }
        .info {
            background: #e0e7ff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 14px;
            color: #4338ca;
            text-align: left;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Fix Handover Status</h1>

        <div class="info">
            <strong>ℹ️ Informasi:</strong><br>
            Script ini memperbaiki status handover yang seharusnya sudah 'transferred' tapi masih 'validated'.
            <br><br>
            Ini terjadi karena sebelumnya sistem hanya mengupdate status pickup, tapi tidak mengupdate status handover.
        </div>

        <?php if (isset($success)): ?>
            <div class="message success">
                <?php echo $success; ?>
            </div>
        <?php endif; ?>

        <?php if (isset($error)): ?>
            <div class="message error">
                <?php echo $error; ?>
            </div>
        <?php endif; ?>

        <a href="dashboard.php" class="btn">← Kembali ke Dashboard</a>
    </div>
</body>
</html>
