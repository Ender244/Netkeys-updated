# NetKeys - Netflix Key Distribution System

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Ender244/netkeys.git
cd netkeys
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the server:**
```bash
python app.py
```

5. **Access the application:**
```
Home: http://localhost:5000
Login: http://localhost:5000/login.html
Redeem: http://localhost:5000/redeem.html
Admin Panel: http://localhost:5000/admin.html
```

---

## 🔐 Security Setup

### Change Admin Password

1. Open `app.py`
2. Find this line:
```python
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()
```
3. Replace `'admin123'` with your secure password
4. Restart the server

### Protect Secret Key

⚠️ **IMPORTANT:** The `secret.key` file is auto-generated and should NEVER be committed:
- It's already in `.gitignore`
- Keep it safe - it encrypts all your data
- Back it up securely
- Never share it

### Environment Variables

Create a `.env` file (not tracked by git):
```bash
ADMIN_PASSWORD=your_secure_password_here
FLASK_SECRET_KEY=your_secret_key
FLASK_ENV=production
```

Then update `app.py` to read from `.env`

---

## 📁 File Structure

```
netkeys/
├── app.py                      # Flask backend (main server)
├── nf-token-generator.py       # Cookie validator
├── index.html                  # Home page
├── login.html                  # User login
├── admin.html                  # Admin panel
├── redeem.html                 # Key redemption
├── inventory.html              # User inventory
├── guidelines.html             # Usage guidelines
├── support.html                # Support page
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore file
├── README.md                   # This file
│
├── [AUTO-GENERATED - DO NOT COMMIT]
├── secret.key                  # Encryption key (BACKUP SAFELY)
├── stock.enc                   # Encrypted stock data
├── users.json                  # User data (in .gitignore)
└── sessions.json               # Session data (in .gitignore)
```

---

## 🔌 API Endpoints

### Authentication
```
POST /api/login
  Body: {"email": "user@example.com"}
  Returns: {"success": true, "token": "...", "email": "..."}

POST /api/admin/login
  Body: {"password": "admin123"}
  Returns: {"success": true, "token": "..."}

POST /api/logout
  Headers: Authorization: Bearer {token}
  Returns: {"success": true}
```

### Stock Management (Admin)
```
GET /api/stock
  Headers: Authorization: Bearer {admin_token}
  Returns: [{id, key, nftoken, status, ...}]

POST /api/stock/upload
  Headers: Authorization: Bearer {admin_token}
  Body: multipart/form-data (files)
  Returns: {"success": true, "added": N}
```

### User Operations
```
POST /api/stock/use
  Headers: Authorization: Bearer {user_token}
  Returns: {success, key, nftoken, ...}

GET /api/inventory
  Headers: Authorization: Bearer {user_token}
  Returns: {email, keys_used, keys[], ...}

POST /api/auto-renew
  Headers: Authorization: Bearer {user_token}
  Body: {"nftoken": "..."}
  Returns: {"success": true, "nftoken": "...", "message": "..."}
```

---

## 🛠️ Troubleshooting

### "Cannot find module 'nf-token-generator'" 
✅ The file is included in the repo. Make sure it's in the same directory as `app.py`

### "Port 5000 already in use"
Change the port in `app.py`:
```python
app.run(debug=True, port=5001)  # Use 5001 instead
```

### Cookie validation not working
- Check that `nf-token-generator.py` is executable:
  ```bash
  chmod +x nf-token-generator.py  # macOS/Linux
  ```
- Ensure Python 3 is installed: `python --version`

### Data not persisting
- Check file permissions in the directory
- Ensure `stock.enc` is readable/writable
- Verify `secret.key` exists

---

## 📚 Usage

### For Users:
1. Go to `http://localhost:5000/login.html`
2. Enter your email
3. Go to `http://localhost:5000/redeem.html`
4. Click "REDEEM KEY" to get a Netflix key
5. Select your device and open the activation URL
6. View your history in inventory

### For Admins:
1. Go to `http://localhost:5000/admin.html`
2. Enter password: `admin123` (change this!)
3. Upload `.txt` files containing Netflix cookies
4. System generates keys and validates cookies
5. Monitor stock in real-time

---

## ⚖️ Legal Notice

This project is for **educational purposes only**. Unauthorized access to accounts and credential distribution may violate:
- Netflix Terms of Service
- Local computer fraud laws
- Data protection regulations

Use responsibly and ethically.

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Support

For issues or questions, open a GitHub issue or check the support page.
