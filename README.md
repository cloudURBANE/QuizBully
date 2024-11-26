# IT Support & Knowledge Quiz Bot 🤖

🚀 A versatile Discord bot for IT professionals and learners to test their knowledge, receive hints, and track their progress in real-time.

---

## **Features**
- 📚 **Interactive Quizzes**: Tackle questions across various IT domains with easy, medium, and hard difficulties.
- 🕒 **Timed Questions**: Keep up with the pace through countdown timers.
- 🏆 **Leaderboard**: Compete with others and see your performance instantly.
- 💡 **Hints & Feedback**: Learn from mistakes with detailed explanations.
- 🤓 **AI-Powered Assistance**: Chat with OpenAI for better insights on quiz topics.
- 💾 **MongoDB Integration**: Dynamically fetch questions and update data.
- 🎭 **Colorful Progress Bars**: See your quiz journey in style!

---

## **Tech Stack**
- **Language**: Python
- **Libraries**: `discord.py`, `asyncio`, `openai`, `pymongo`
- **Database**: MongoDB Atlas
- **Bot Hosting**: Cloud or local deployment

---

## **Setup Instructions**
1. **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/quiz-bot.git
    cd quiz-bot
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure Environment Variables**:
    - Create a `.env` file with the following:
        ```plaintext
        DISCORD_TOKEN=your_discord_bot_token
        OPENAI_API_KEY=your_openai_api_key
        MONGO_URI=your_mongodb_connection_uri
        ```

4. **Run the Bot**:
    ```bash
    python bot.py
    ```
---

## **Getting Started**
Follow these steps to see the bot in action:

### 1. **Getting The Quiz Started**
   ![Getting The Quiz Started](https://i.imgur.com/29Wam5g.png)

   Message the Bot: Use the command `!q` to start QuizBully!

### 2. **Starting a Quiz**
   ![Starting a Quiz](https://i.imgur.com/zq3PmV3.png)

   View: React with 💚, 💛, or 💜 to choose difficulty.

### 3. **Selecting Quiz Type**
   ![Selecting Quiz Type](https://i.imgur.com/K7U1VCt.png)

   View: Choose from the following: 1️⃣ Generate a new Quiz, 2️⃣ Select from existing topics, Go back, Cancel the quiz.

### 4. **Generating New Questions**
   ![Generating New Questions](https://i.imgur.com/9h5vpTA.png)

   Example: Enter "CompTIA Network+" to generate questions on the topic.

### 5. **Quiz Question Embed**
   ![Quiz Question Embed](https://i.imgur.com/N4lR9Yy.png)

   View: Question embed with color-coded difficulty that varies the speed of the question timer.

---

## **Future Enhancements**
- 🌐 Multi-language Support
- 💬 Enhanced AI Conversation Context

---

## **Contributing**
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add feature'`).
4. Push the branch (`git push origin feature-name`).
5. Create a pull request.

---

## **License**
This project is licensed under the [MIT License](LICENSE).

---

## **Contact**
For questions or contributions:
- **Developer**: [Your Name](https://github.com/your-username)
- **Email**: your.email@example.com
