# P-Suite: The All-in-One Web Production Suite

P-Suite is a powerful, interactive web application built with Flask and Socket.IO. It provides a suite of tools designed to help web developers optimize, analyze, and secure their projects before deployment. Users can upload a project as a ZIP file, select from various processing options, and receive real-time feedback and downloadable results.

This project serves as a comprehensive demonstration of a modern web application architecture, featuring user authentication, a credit-based usage system, real-time client-server communication, and the integration of external command-line tools for backend processing.

---

## ✨ Key Features

### Frontend Optimizer
- **Asset Minification:** Compresses HTML, CSS, and JavaScript files to reduce their size.
- **Image Optimization:** Optimizes JPG/PNG images and SVGs without significant quality loss.
- **CSS Purging:** Intelligently removes unused CSS rules from your stylesheets.
- **JavaScript Obfuscation:** Makes your client-side code harder to read and reverse-engineer.
- **Security Hardening:** Automatically adds a Content-Security-Policy (CSP) meta tag to HTML files.
- **Critical CSS Generation (`PRO` Feature):** Extracts and inlines critical-path CSS for lightning-fast initial page loads.

### Backend Analyzer (Python)
- **Code Style Linting:** Uses `Flake8` to check for PEP 8 compliance and logical errors.
- **Dead Code Detection:** Employs `Vulture` to find and report unused code, helping to clean up your codebase.

### Security Scanner
- **Dependency Vulnerability Scanning:**
    - Audits Python `requirements.txt` using `pip-audit`.
    - Audits Node.js `package-lock.json` using `npm audit` (`PREMIUM` Feature).
- **Hardcoded Secret Detection:** Scans source code for patterns that look like exposed API keys, tokens, or passwords.
- **Debug Mode Checks:** Looks for common ways debug mode is left enabled in production code.

### Platform Features
- **User Authentication:** Secure user registration and login system.
- **Credit System:** Users receive free credits upon registration and can upgrade for more. Tool usage consumes credits.
- **Subscription Tiers:** Mocked `Free`, `Premium`, and `Pro` plans that unlock different features.
- **Real-time Progress:** A live console, powered by WebSockets, shows the step-by-step progress of each task.
- **Interactive UI:** A modern, responsive interface with drag-and-drop file uploads and dynamic results display.

---

## 📸 Screenshots

| Homepage | Frontend Optimizer Tool |
| :---: | :---: |
|  |  |

| Live Processing Console | Results View with File Tree |
| :---: | :---: |
|  |  |

---

## 🛠️ Technology Stack

- **Backend:**
  - **Framework:** Flask
  - **Real-time Communication:** Flask-SocketIO
  - **Database ORM:** Flask-SQLAlchemy
  - **Authentication:** Flask-Login
  - **Database:** SQLite (for development)

- **Frontend:**
  - **Templating:** Jinja2
  - **Styling:** Plain CSS3 with modern features (CSS Variables, Flexbox, Grid)
  - **JavaScript:** ES6+ (Classes, async/await), Socket.IO Client

- **Core Tooling (System Dependencies):**
  - **Python Tools:** `pip-audit`, `Pillow`, `cssmin`, `minify-html`, `beautifulsoup4`, `vulture`, `flake8`
  - **Node.js CLI Tools:** `javascript-obfuscator`, `terser`, `svgo`, `purgecss`, `critical`, `npm`

---

## 🚀 Setup and Installation

Follow these steps to get the P-Suite application running on your local machine.

### 1. Prerequisites
- [Git](https://git-scm.com/)
- [Python 3.8+](https://www.python.org/downloads/) and `pip`
- [Node.js 16+](https://nodejs.org/) and `npm`

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/psuite-project.git
cd psuite-project
```

### 3. Set Up a Python Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.

```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

### 4. Install Python Dependencies
Install all the required Python packages from the `requirements.txt` file.
```bash
pip install Flask Flask-SocketIO Flask-SQLAlchemy Flask-Login Pillow cssmin minify-html beautifulsoup4 vulture flake8 Werkzeug gunicorn eventlet
```

### 5. Install Global Node.js CLI Tools
The processing backend calls several command-line tools. These must be installed globally via `npm`.
```bash
npm install -g javascript-obfuscator terser svgo purgecss critical
```

### 6. Run the Application
The application uses `eventlet` as the Socket.IO web server.
```bash
python run.py
```

The application will now be running at **http://127.0.0.1:5000**.

---

## 📖 How to Use

1.  **Register an Account:** Navigate to the site and create a new account. You'll automatically receive 10 free credits.
2.  **Log In:** Use your new credentials to log in.
3.  **Select a Tool:** Choose one of the tools from the navigation or the homepage (Optimizer, Analyzer, or Scanner).
4.  **Upload Your Project:** Drag and drop a `.zip` file of your project onto the designated area, or use the file browser.
5.  **Configure Options:** Select any available options for the chosen tool.
6.  **Run the Process:** Click the main button to start the process (this will deduct 1 credit).
7.  **Watch the Console:** Observe the real-time log of the operations being performed.
8.  **View Results:** Once complete, you can view the results. For the optimizer, this includes a summary report, an interactive file tree, and a link to download the optimized ZIP file.

---

## 📂 Project Structure

The project uses a Flask Blueprint architecture to organize its code logically.

```
psuite-project/
├── instance/
│   └── suite.db           # SQLite database file
├── psuite/
│   ├── blueprints/        # Contains the application's blueprints
│   │   ├── auth.py        # Authentication routes (login, register)
│   │   ├── main.py        # Core routes (home, pricing, account)
│   │   └── tools.py       # Tool routes and Socket.IO handlers
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/script.js
│   ├── templates/         # HTML templates
│   ├── __init__.py        # Application factory
│   ├── models.py          # SQLAlchemy database models (User)
│   └── processing.py      # Backend logic for all tool processing
├── venv/                    # Python virtual environment
├── run.py                 # Main entry point to run the application
└── README.md              # This file
```

---

## 💡 Future Improvements

- [ ] **Real Payment Integration:** Implement Stripe or PayPal for actual subscription management.
- [ ] **More Analyzers:** Add tools for Dockerfile linting, accessibility testing (a11y), or performance analysis (Lighthouse).
- [ ] **User History:** Allow users to view and re-download results from past runs.
- [ ] **Team & Organization Support:** Introduce user roles and permissions for team collaboration.
- [ ] **Containerization:** Provide a `Dockerfile` for easy deployment.

---

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
