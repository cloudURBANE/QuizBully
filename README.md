# IT Support & Knowledge Quiz Bot 🤖

🚀 A versatile Discord bot designed to help IT professionals and learners test their knowledge, receive helpful hints, and track their progress efficiently.

---

## **Core Features**
- 📚 **Interactive Quizzes**: Questions across IT domains with varying difficulty levels.
- 🕒 **Timed Challenges**: Stay sharp with countdown timers.
- 🏆 **Leaderboard**: Compete and see your ranking instantly.
- 💡 **Hints & Explanations**: Learn from mistakes with clear feedback.
- 🤓 **AI-Powered Insights**: Get assistance on quiz topics with integrated AI.
- 💾 **MongoDB Integration**: Fetch and update questions seamlessly.

---

## **Tech Stack**
- **Language**: Python
- **Key Libraries**: `discord.py`, `asyncio`, `pymongo`
- **Database**: MongoDB Atlas
- **Deployment**: Cloud or local hosting options

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

## **Quick Start Guide**

### 1. **Starting the Quiz**
   ![Getting The Quiz Started](https://i.imgur.com/LOR6eKK.png)

   Use the command `!q` to initiate a quiz.

### 2. **Choosing Difficulty**
   ![Starting a Quiz](https://i.imgur.com/zq3PmV3.png)

   React with 💚, 💛, or 💜 to choose the quiz difficulty level.

### 3. **Select Quiz Type**
   ![Selecting Quiz Type](https://i.imgur.com/K7U1VCt.png)

   Choose an option: 1️ Generate new questions, 2️ Pick existing topics, 3 cancel, or 4 Go back.

### 4. **Generate Quizzes**
   ![Generating New Quizzes](https://i.imgur.com/9h5vpTA.png)

   Example: Enter your topic of choice to start generating questions using OPENAI's ChatGPT "4o" Model.

### 5. **Question Embed**
   ![Quiz Question Embed](https://i.imgur.com/N4lR9Yy.png)

   View: Question & answer choices and emoji reactions as your way of answer input with color-coded difficulty timers.

---

## **Contributing**
We welcome contributions! Here’s how to get started:
1. Fork the repository.
2. Create a branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add feature'`).
4. Push to your branch (`git push origin feature-name`).
5. Submit a pull request.

---

## **License**
This project is licensed under the [MIT License](LICENSE).

---

## **Contact**
For questions or contributions:
- **GitHub**: [Kyle A Dean](https://github.com/cloudURBANE)
- **LinkedIn**: [My LinkedIn Profile](https://www.linkedin.com/in/kyleaustin-dean/)
