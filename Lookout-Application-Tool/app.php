<?php
/**
 * Lookout Application Submission Tool (Simple PHP 8)
 * * Update: Added OAuth2 Token Auto-Generation
 * * Requirements:
 * - PHP 8.0+
 * - cURL extension enabled
 * - file_uploads = On in php.ini
 * - upload_max_filesize and post_max_size configured appropriately
 */

$message = '';
$messageType = ''; // 'success' or 'error'
$responseDat = null;
$generatedToken = null;

/**
 * Helper function to exchange App Key for Token
 */
function getOAuthToken($host, $appKey, $tokenPath = '/oauth/token') {
    $url = "https://" . str_replace(['https://', 'http://'], '', $host) . $tokenPath;
    
    $ch = curl_init();
    
    // Attempting Standard OAuth2 Client Credentials Flow
    // If your key requires a different parameter (e.g., 'apikey' instead of 'client_id'), change it here.
    $postData = http_build_query([
        'grant_type' => 'client_credentials',
        'client_id'  => $appKey
        // 'client_secret' => '' // Uncomment if your key is actually a pair
    ]);

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Accept: application/json'
    ]);
    
    // Basic Auth fallback (Uncomment if Lookout requires the key in Basic Auth header instead of body)
    // curl_setopt($ch, CURLOPT_USERPWD, "$appKey:");

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error) {
        throw new Exception("Token Generation Connection Error: " . $error);
    }

    $data = json_decode($response, true);
    
    if ($httpCode >= 200 && $httpCode < 300 && isset($data['access_token'])) {
        return $data['access_token'];
    } else {
        $apiError = $data['error_description'] ?? $data['error'] ?? 'Unknown error';
        throw new Exception("Failed to generate token (HTTP $httpCode): $apiError");
    }
}

// Handle Form Submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $apiHost = rtrim($_POST['api_host'] ?? '', '/');
    $token = trim($_POST['api_token'] ?? '');
    $appKey = trim($_POST['app_key'] ?? '');
    $submissionType = $_POST['submission_type'] ?? 'url';

    try {
        if (empty($apiHost)) {
            throw new Exception("API Host is required.");
        }

        // --- TOKEN GENERATION LOGIC ---
        // If Token is empty but Key is provided, try to generate it.
        if (empty($token) && !empty($appKey)) {
            $token = getOAuthToken($apiHost, $appKey);
            $generatedToken = "Token generated successfully using Application Key.";
        } elseif (empty($token)) {
            throw new Exception("Please provide either an OAuth Token OR an Application Key.");
        }

        // --- MAIN API REQUEST ---
        $ch = curl_init();
        $headers = [
            "Authorization: Bearer $token",
            "Accept: application/json"
        ];
        
        $url = "";
        
        if ($submissionType === 'store_url') {
            // --- HANDLE STORE URL SUBMISSION ---
            $storeUrl = $_POST['store_url'] ?? '';
            if (empty($storeUrl)) {
                throw new Exception("Please enter a Store URL.");
            }

            $endpoint = "/api/v1/applications/submissions/store";
            $query = http_build_query(['url' => $storeUrl]);
            $url = "https://" . str_replace(['https://', 'http://'], '', $apiHost) . $endpoint . "?" . $query;
            
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, ""); 

        } elseif ($submissionType === 'file_upload') {
            // --- HANDLE FILE UPLOAD SUBMISSION ---
            if (!isset($_FILES['app_file']) || $_FILES['app_file']['error'] !== UPLOAD_ERR_OK) {
                throw new Exception("File upload failed. Check PHP upload_max_filesize settings.");
            }

            $fileTmpPath = $_FILES['app_file']['tmp_name'];
            $fileName = $_FILES['app_file']['name'];
            $fileType = $_FILES['app_file']['type'];

            $endpoint = "/api/v1/applications/submissions/file";
            $url = "https://" . str_replace(['https://', 'http://'], '', $apiHost) . $endpoint;

            $cFile = new CURLFile($fileTmpPath, $fileType, $fileName);
            $postData = ['file' => $cFile];

            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
        }

        // Common cURL Options
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_FAILONERROR, false);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlError = curl_error($ch);
        
        curl_close($ch);

        if ($curlError) {
            throw new Exception("Connection Error: " . $curlError);
        }

        $responseData = json_decode($response, true);

        if ($httpCode >= 200 && $httpCode < 300) {
            $message = "Submission Successful!";
            $messageType = 'success';
        } else {
            $errorMsg = $responseData['error'] ?? 'Unknown API Error';
            $message = "API Error ($httpCode): " . $errorMsg;
            $messageType = 'error';
        }

    } catch (Exception $e) {
        $message = $e->getMessage();
        $messageType = 'error';
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lookout App Submission Tool</title>
    <style>
        :root {
            --primary: #0052cc;
            --bg: #f4f5f7;
            --surface: #ffffff;
            --border: #dfe1e6;
            --text: #172b4d;
            --success: #36b37e;
            --error: #ff5630;
            --info: #4c9aff;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            display: flex;
            justify-content: center;
            padding-top: 50px;
            margin: 0;
            padding-bottom: 50px;
        }
        .container {
            background: var(--surface);
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 600px;
        }
        h2 { margin-top: 0; color: var(--primary); }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid var(--border);
            border-radius: 4px;
            box-sizing: border-box;
        }
        .tabs { display: flex; margin-bottom: 1.5rem; border-bottom: 2px solid var(--border); }
        .tab {
            padding: 0.75rem 1.5rem;
            cursor: pointer;
            font-weight: 600;
            color: #6b778c;
        }
        .tab.active {
            color: var(--primary);
            border-bottom: 2px solid var(--primary);
            margin-bottom: -2px;
        }
        .section { display: none; }
        .section.active { display: block; }
        
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
        }
        button:hover { background-color: #0047b3; }
        
        .alert {
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1.5rem;
        }
        .alert.success { background-color: #e3fcef; color: #006644; border: 1px solid #abf5d1; }
        .alert.error { background-color: #ffebe6; color: #bf2600; border: 1px solid #ffbdad; }
        .alert.info { background-color: #deebff; color: #0747a6; border: 1px solid #b3d4ff; }
        
        .response-box {
            background: #f4f5f7;
            padding: 1rem;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            margin-top: 1rem;
            border: 1px solid var(--border);
            overflow-x: auto;
        }
        .hint { font-size: 0.85rem; color: #6b778c; margin-top: 0.25rem; }
        .auth-separator {
            text-align: center; margin: 10px 0; font-size: 0.8rem; color: #999;
            display: flex; align-items: center;
        }
        .auth-separator::before, .auth-separator::after {
            content: ""; flex: 1; border-bottom: 1px solid #eee;
        }
        .auth-separator span { padding: 0 10px; }
    </style>
</head>
<body>

<div class="container">
    <h2>Lookout Submission Tool</h2>
    
    <?php if ($generatedToken): ?>
        <div class="alert info">
            <?php echo htmlspecialchars($generatedToken); ?>
        </div>
    <?php endif; ?>

    <?php if ($message): ?>
        <div class="alert <?php echo $messageType; ?>">
            <?php echo htmlspecialchars($message); ?>
        </div>
    <?php endif; ?>

    <form method="POST" enctype="multipart/form-data">
        <!-- Configuration -->
        <div class="form-group">
            <label for="api_host">API Host</label>
            <input type="text" id="api_host" name="api_host" placeholder="e.g. api.lookout.com" required 
                   value="<?php echo isset($_POST['api_host']) ? htmlspecialchars($_POST['api_host']) : ''; ?>">
        </div>

        <!-- Auth Section -->
        <div style="background: #fafbfc; padding: 15px; border: 1px solid #eee; border-radius: 4px; margin-bottom: 1rem;">
            <label style="color: #42526e; margin-bottom: 10px;">Authentication (Choose One)</label>
            
            <div class="form-group">
                <label for="app_key">Option A: Application Key (Auto-Generate Token)</label>
                <input type="text" id="app_key" name="app_key" placeholder="Enter Application Key to generate token automatically"
                       value="<?php echo isset($_POST['app_key']) ? htmlspecialchars($_POST['app_key']) : ''; ?>">
                <div class="hint">Leave 'Bearer Token' empty to use this.</div>
            </div>

            <div class="auth-separator"><span>OR</span></div>

            <div class="form-group">
                <label for="api_token">Option B: Existing OAuth2 Bearer Token</label>
                <input type="text" id="api_token" name="api_token" placeholder="Paste existing access token here"
                       value="<?php echo isset($_POST['api_token']) ? htmlspecialchars($_POST['api_token']) : ''; ?>">
            </div>
        </div>

        <!-- Tab Selection -->
        <label>Submission Type</label>
        <div class="tabs">
            <div class="tab active" onclick="switchTab('url')">Store URL</div>
            <div class="tab" onclick="switchTab('file')">File Upload</div>
        </div>
        
        <input type="hidden" name="submission_type" id="submission_type" value="store_url">

        <!-- Store URL Section -->
        <div id="section-url" class="section active">
            <div class="form-group">
                <label for="store_url">Apple App Store / Google Play URL</label>
                <input type="text" id="store_url" name="store_url" placeholder="https://play.google.com/store/apps/details?id=..." 
                       value="<?php echo isset($_POST['store_url']) ? htmlspecialchars($_POST['store_url']) : ''; ?>">
            </div>
        </div>

        <!-- File Upload Section -->
        <div id="section-file" class="section">
            <div class="form-group">
                <label for="app_file">Application File (.ipa, .apk, .aab)</label>
                <input type="file" id="app_file" name="app_file" accept=".ipa,.apk,.aab">
                <div class="hint">Max size: <?php echo ini_get('upload_max_filesize'); ?> (Server Config)</div>
            </div>
        </div>

        <button type="submit">Submit for Analysis</button>
    </form>

    <?php if (isset($responseData)): ?>
        <div style="margin-top: 1.5rem;">
            <label>API Response:</label>
            <div class="response-box">
<?php 
    if (isset($responseData['referenceId'])) {
        echo "<strong>Reference ID:</strong> " . htmlspecialchars($responseData['referenceId']) . "\n";
    }
    if (isset($responseData['url'])) {
        echo "<strong>URL:</strong> " . htmlspecialchars($responseData['url']) . "\n";
    }
    // Dump full JSON for debugging details
    echo "\n--- Raw JSON ---\n";
    echo htmlspecialchars(json_encode($responseData, JSON_PRETTY_PRINT)); 
?>
            </div>
        </div>
    <?php endif; ?>
</div>

<script>
    function switchTab(type) {
        // Update hidden input
        document.getElementById('submission_type').value = (type === 'url') ? 'store_url' : 'file_upload';
        
        // Update Tabs UI
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active'); // Assumes click event

        // Toggle Sections
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById('section-' + type).classList.add('active');
    }
    
    // Maintain tab state after POST
    <?php if (isset($_POST['submission_type']) && $_POST['submission_type'] === 'file_upload'): ?>
        document.querySelectorAll('.tab')[1].click();
    <?php endif; ?>
</script>

</body>
</html>
