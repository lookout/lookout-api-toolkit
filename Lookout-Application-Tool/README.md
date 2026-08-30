# Lookout App Submission Tool

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A local Python web application for submitting mobile apps to Lookout for security analysis.

[Features](#features) • [Quick Start](#quick-start) • [Usage](#usage) • [API](#api-endpoints) • [Contributing](#contributing)

</div>

## Features

- **Submit Apps**: Upload IPA/APK/AAB files or submit via Apple/Google Play Store URLs
- **Auto Token Generation**: Automatically exchange Application Key for OAuth2 Bearer Token
- **Check Status**: Query analysis status using reference IDs
- **View History**: Track all submissions in the current session
- **Generate Reports**: Export analysis results in JSON, Summary, or CSV formats

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**

## Usage

### Authentication

You need one of the following:
- **Application Key**: The tool will auto-generate an OAuth2 token
- **Bearer Token**: Use an existing OAuth2 token

### Submitting Apps

**Via Store URL:**
1. Paste the Apple App Store or Google Play URL
2. Click "Submit for Analysis"

**Via File Upload:**
1. Switch to "File Upload" tab
2. Drag & drop or click to select an IPA, APK, or AAB file
3. Click "Submit for Analysis"

### Checking Status

1. Go to "Check Status" tab
2. Enter the Reference ID from your submission
3. Click "Check Status" or "List All" for all submissions

### Generating Reports

1. Go to "Reports" tab
2. Enter the Reference ID
3. Select format (JSON, Summary, or CSV)
4. Click "Generate Report"

## API Endpoints Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/applications/submissions/file` | Submit app file |
| POST | `/api/v1/applications/submissions/store` | Submit store URL |
| GET | `/api/v1/applications/analyses/{reference_id}` | Get analysis status |
| GET | `/api/v1/applications/analyses` | List all analyses |

## Requirements

- Python 3.8+
- Flask 2.0+
- Requests library
- Valid Lookout API credentials (Application Key or Bearer Token)

## Installation & Setup

### 1. Navigate to the Project Directory

```bash
cd Lookout-Application-Tool
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Credentials

Copy the example config file and add your Lookout API credentials:

```bash
cp config.example.py config.py
```

Open `config.py` and fill in your credentials:

```python
API_HOST = "api.lookout.com"
APP_KEY = "your_application_key_here"   # Your Application Key
# OR
BEARER_TOKEN = "your_bearer_token_here"  # Existing OAuth2 token
```

**`config.py` is listed in `.gitignore` and will never be committed.** Alternatively, supply credentials as environment variables at runtime:

```bash
export LOOKOUT_APP_KEY="your_application_key_here"
python app_improved.py
```

### 4. Run the Application

```bash
python app_improved.py
```

### 5. Open in Browser

Navigate to: **http://localhost:5000**

## Project Structure

```
Lookout-Application-Tool/
├── app_improved.py                   # Enhanced Flask application with improved UI/UX
├── app.py                            # Original Flask application
├── config.example.py                 # Credential template — copy to config.py and fill in
├── config.py                         # Your local credentials (git-ignored, not committed)
├── requirements.txt                  # Python dependencies
├── README.md                         # This file
├── CHANGELOG.md                      # Improvement summary
├── IMPROVEMENTS.md                   # Detailed UI/UX improvements
├── .gitignore                        # Git ignore patterns
└── application_submission_api.json   # API documentation
```

## File Size Limits

- Maximum upload: 2GB (configurable in `app.py`)
- Supported formats: `.ipa`, `.apk`, `.aab`

## Security Notes

- Tokens are stored in browser memory only (cleared on refresh)
- No credentials are persisted to disk
- Use HTTPS in production environments
- Keep your `config.py` file secure - never commit API keys
- Use environment variables for production deployments

## Development

### Running Tests

```bash
# Add test framework and run tests
python -m pytest tests/
```

### Code Quality

```bash
# Linting
flake8 app_improved.py

# Type checking
mypy app_improved.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Common Issues

**Issue:** "Token generation failed"
- **Solution:** Verify your API credentials in `config.py` are correct (copy from `config.example.py` if needed)

**Issue:** "Connection timeout"
- **Solution:** Check your network connection and API host URL

**Issue:** "File upload fails"
- **Solution:** Ensure file is under 2GB and in correct format (.ipa, .apk, .aab)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Powered by [Lookout API](https://www.lookout.com/)
- UI/UX inspired by modern web accessibility standards

## Support

For issues, questions, or contributions, please:
- Open an issue on GitHub
- Check existing documentation in `IMPROVEMENTS.md`
- Review the API documentation in `application_submission_api.json`
