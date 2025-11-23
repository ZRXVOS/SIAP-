<?php
/**
 * Simple Auto-Deploy Script
 * Download file langsung dari GitHub
 *
 * CARA PAKAI:
 * 1. Upload file ini ke public_html/ via File Manager Hostinger
 * 2. Akses: https://monyonyo.site/deploy-simple.php?key=SIAP2024&update=debug
 */

$deploy_key = 'SIAP2024';

if (!isset($_GET['key']) || $_GET['key'] !== $deploy_key) {
    die('❌ Unauthorized access');
}

echo "<h1>🚀 Simple Auto-Deploy</h1>";
echo "<pre>";

// GitHub raw URLs - UPDATE THESE DENGAN URL REPO ANDA
$github_user = 'YOUR_GITHUB_USERNAME';  // <-- GANTI INI
$github_repo = 'SIAP-';                  // <-- GANTI INI
$github_branch = 'claude/fix-hostinger-app-errors-01MaD2mnzzp4Da4QPDoPoRsA';

$files_to_update = [
    'debug' => [
        'source' => "https://raw.githubusercontent.com/$github_user/$github_repo/$github_branch/admin/debug-selisih-calculation.php",
        'dest' => __DIR__ . '/admin/debug-selisih-calculation.php'
    ],
    // Tambahkan file lain di sini jika perlu
    // 'laporan' => [
    //     'source' => "https://raw.githubusercontent.com/$github_user/$github_repo/$github_branch/admin/laporan.php",
    //     'dest' => __DIR__ . '/admin/laporan.php'
    // ],
];

$update = $_GET['update'] ?? 'all';

if ($update === 'all') {
    $to_update = $files_to_update;
} elseif (isset($files_to_update[$update])) {
    $to_update = [$update => $files_to_update[$update]];
} else {
    die("❌ Invalid update parameter. Available: " . implode(', ', array_keys($files_to_update)));
}

foreach ($to_update as $name => $file) {
    echo "\n📥 Downloading $name...\n";
    echo "From: {$file['source']}\n";
    echo "To:   {$file['dest']}\n";

    $content = file_get_contents($file['source']);

    if ($content === false) {
        echo "❌ Failed to download $name\n";
        continue;
    }

    // Backup existing file
    if (file_exists($file['dest'])) {
        $backup = $file['dest'] . '.backup.' . date('YmdHis');
        copy($file['dest'], $backup);
        echo "✓ Backup created: $backup\n";
    }

    // Write new file
    $result = file_put_contents($file['dest'], $content);

    if ($result !== false) {
        echo "✅ Successfully updated $name (" . strlen($content) . " bytes)\n";
    } else {
        echo "❌ Failed to write $name\n";
    }
}

echo "\n==================================\n";
echo "✅ Deploy completed!\n";
echo "</pre>";

echo "<hr>";
echo "<p><a href='admin/dashboard.php'>← Kembali ke Dashboard</a></p>";
?>
