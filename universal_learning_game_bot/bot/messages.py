import os

WELCOME_MESSAGE = """Welcome to Universal Learning Game! 🎓

Ready to improve your knowledge and challenge yourself?

Your learning journey starts here.

Press the <b>🚀 OPEN GAME</b> button on your keyboard below to launch the learning platform!

📌 Reminder: Come back every day and press START or tap OPEN GAME to access your learning platform again.

Good luck! 🚀"""

def get_game_link_message(url: str = None):
    target_url = url or os.environ.get("WEB_APP_URL", "https://universallearninggame.vercel.app/")
    return f"""🎮 <b>Universal Learning Game</b>

Your platform is ready! Tap the button below or open the link directly in your browser:

🔗 <a href="{target_url}">{target_url}</a>

📌 <i>The persistent <b>🚀 OPEN GAME</b> button remains below at all times for instant daily access.</i>"""

HOW_TO_USE_MESSAGE = """📖 <b>How to Use Universal Learning Game</b>

1. <b>Persistent Keyboard:</b> Look at the permanent action buttons pinned at the bottom of your chat screen.
2. <b>Launch the Game:</b> Tap <b>🚀 OPEN GAME</b> anytime to receive your direct clickable browser access link.
3. <b>Explore the 10 Study Modes:</b> Enjoy Learn Mode, Classic Quiz, Flashcards (Spaced Repetition), Matching Game, and Final Exam simulations in your browser.
4. <b>Daily Engagement:</b> Return every day, tap <b>🚀 OPEN GAME</b> or send <b>/start</b> to maintain your daily study routine!"""

ABOUT_MESSAGE = """ℹ️ <b>About Universal Learning Game</b>

<b>Universal Learning Game</b> is a universal educational platform designed to transform complex lecture materials, PowerPoint presentations, and questions into an engaging study game.

✨ <b>Platform Highlights:</b>
• <b>10 Interactive Game Modes:</b> Learn, Quiz, Flashcards (SRS), Matching, Fill in the Blanks, True/False, and Final Exam.
• <b>Slide Evidence Synchronization:</b> Real-time theoretical proof from verified lecture slides.
• <b>Bilingual Support:</b> English questions with accurate Uzbek terminology.
• <b>Browser-Optimized:</b> Opens directly in your browser without requiring Mini App permissions.

Current Course: <b>Lecture 5 · The Verb and Verbal Categories</b> (61 Questions & 51 Slides)"""

UPDATES_MESSAGE = """📢 <b>Latest Announcements & Updates</b>

<b>Version 2.5 Release Notes:</b>
• 🎓 <b>Lecture 5 is Live:</b> 61 comprehensive questions and 51 lecture slides covering Theoretical English Grammar.
• ⌨️ <b>Persistent Reply Keyboard:</b> Action buttons are now permanently pinned at the bottom of your chat for instant one-tap access.
• 🌐 <b>External Browser Support:</b> Game opens directly in your default browser without Mini App restrictions.
• 🔄 <b>Dynamic Answer Shuffling:</b> Option positions are randomized on every round.
• ⏩ <b>Skip & Navigation:</b> Freely move between questions with Previous/Next controls."""

def get_help_support_message():
    support_username = os.environ.get("SUPPORT_USERNAME", "Odilxon_Support").lstrip("@")
    return f"""🆘 <b>Help & Support</b>

Need assistance, spotted an issue, or have a suggestion?

• <b>Direct Telegram Support:</b> @{support_username}
• <b>Service Status:</b> Online 24/7 on Vercel Serverless Architecture.

<i>Use the permanent buttons at the bottom of the chat to navigate.</i>"""

ADMIN_ACCESS_DENIED = """⛔ <b>Access Denied</b>

This command is restricted to system administrators only.

Make sure your Telegram User ID is configured in the <code>ADMIN_ID</code> environment variable."""

def get_admin_help_message():
    return """⚙️ <b>Admin Dashboard Controls</b>

<b>Available Admin Commands:</b>
• <code>/admin</code> or <code>/admin stats</code> — View system stats, total users, daily active counts, and recent registrations.
• <code>/broadcast &lt;message&gt;</code> — Send an official announcement to all active registered users.

<i>Example broadcast:</i>
<code>/broadcast 📢 Important Update!\n\nTo continue using Universal Learning Game, return to our Telegram bot and tap 🚀 OPEN GAME.\n\nSee you there! 🚀</code>"""
