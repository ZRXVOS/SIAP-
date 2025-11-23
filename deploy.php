<?php
/**
 * Auto-Deploy Script for Hostinger
 * Upload file ini ke public_html/ (root folder)
 * Akses: https://monyonyo.site/deploy.php?key=SIAP2024deploy
 *
 * CARA PAKAI:
 * 1. Upload file ini ke public_html/ via File Manager
 * 2. Akses URL: https://monyonyo.site/deploy.php?key=SIAP2024deploy
 * 3. Script akan auto-pull dari git repository
 */

// Security key
$deploy_key = 'SIAP2024deploy';

// Check key
if (!isset($_GET['key']) || $_GET['key'] !== $deploy_key) {
    die('Unauthorized access. Missing or invalid key.');
}

echo "<h1>🚀 Auto-Deploy Script</h1>";
echo "<pre>";

// Path ke git repository
$git_path = __DIR__;

// Change ke directory
chdir($git_path);

echo "Current directory: " . getcwd() . "\n";
echo "==================================\n\n";

// Check if git exists
if (!file_exists('.git')) {
    echo "❌ ERROR: Git repository tidak ditemukan!\n";
    echo "Directory ini bukan git repository.\n";
    exit(1);
}

echo "✓ Git repository detected\n\n";

// Git pull
echo "📥 Pulling latest changes from git...\n";
echo "==================================\n";
exec('git pull origin claude/fix-hostinger-app-errors-01MaD2mnzzp4Da4QPDoPoRsA 2>&1', $output, $return_code);

foreach ($output as $line) {
    echo $line . "\n";
}

if ($return_code === 0) {
    echo "\n✅ Deploy berhasil!\n";
    echo "==================================\n";
    echo "File sudah ter-update dari git repository.\n\n";

    // Show changed files
    exec('git log -1 --oneline', $log);
    echo "Latest commit: " . $log[0] . "\n";
} else {
    echo "\n❌ Deploy gagal!\n";
    echo "Return code: " . $return_code . "\n";
}

echo "</pre>";

echo "<hr>";
echo "<p><a href='admin/dashboard.php'>← Kembali ke Dashboard</a></p>";
?>
