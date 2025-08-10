import os
import time
import traceback
import discord
from discord.ext import commands
import asyncio
import logging
import random
import inspect
from typing import Callable, Dict, List, Tuple, Union
from collections import defaultdict
from datetime import datetime, timedelta
from openai import OpenAI, AsyncOpenAI
import re
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection setup
MONGO_URI = os.getenv("MONGO_URI")
questions_collection = None
if MONGO_URI:
    try:
        client2 = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        database_name = "Quiz_Set_Data_Collections_2023"
        collection_name = "QuizBully_2023"
        db = client2[database_name]
        questions_collection = db[collection_name]
    except Exception as e:
        logging.warning(f"MongoDB not configured or unreachable: {e}")

# OpenAI API setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Discord bot token
TOKEN = os.getenv("DISCORD_TOKEN")

# Global variables
topic = ""
quiz_data = {
    "easy": [],
    "medium": [],
    "hard": []
}

# Logging setup
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
typing_colors = [
    "#50C878",  # EmeraldLeaf
    "#4E6649",  # JungleFern
    "#00A86B",  # RainforestGlow
    "#20452A",  # VineyardGreen
    "#3E6D50",  # PalmParadise
]

# Randomly select a color for the typing effect
selected_typing_color = random.choice(typing_colors)
REACTION_OPTIONS = ["🇦", "🇧", "🇨", "🇩"]
DIFFICULTY_TIMES = {"easy": 25, "medium": 20, "hard": 15}
DIFFICULTY_EMOJIS = {"easy": "💚", "medium": "💛", "hard": "❤️"}
reaction_counter = {}
real_time_leaderboard_message_id = None
quiz_participation_counter = {}
quiz_completion_counter = 0
question_response_time = {}

DIFFICULTY_TIPS = {}

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')


async def get_dm_channel_for_user(user: discord.User):
    dm_channel = user.dm_channel
    if not dm_channel:
        logging.info(f" No DM channel found for user ID {user.id}.")
        logging.info(f"Attempting to create a new DM channel for user ID {user.id}...")
        try:
            dm_channel = await user.create_dm()
            if dm_channel:
                logging.info(f"DM channel successfully created for user ID {user.id}.")
            else:
                logging.warning(f"Created DM channel object for user ID {user.id} is None. This is unexpected.")
        except Exception as e:
            logging.error(f" Exception encountered while creating DM for user ID {user.id}: {e}")
    else:
        logging.info(f"Located existing DM channel for user ID {user.id}.")
    return dm_channel

# Corrected line:
last_reaction_time = defaultdict(lambda: datetime.utcnow())

color_scheme = {
    'easy': discord.Color.from_rgb(102, 255, 102),
    'medium': discord.Color.from_rgb(255, 255, 102),
    'hard': discord.Color.from_rgb(255, 102, 102)
}

class ProgressBarThemes:
    @staticmethod
    def generate_gradient(start, middle, end, steps):
        half_steps = steps // 2
        first_half_gradient = []
        for i in range(half_steps):
            first_half_gradient.append(
                '#' + ''.join([format(int(s + (m - s) * (i / half_steps)), '02x') for s, m in zip(start, middle)])
            )
        second_half_gradient = []
        for i in range(half_steps):
            second_half_gradient.append(
                '#' + ''.join([format(int(m + (e - m) * (i / half_steps)), '02x') for m, e in zip(middle, end)])
            )
        return tuple(first_half_gradient + second_half_gradient)

    BASIC = {
        'filled_char': '✦',
        'empty_char': '□',
        'border_chars': ('╔✨', '✨╗'),
        'colors': generate_gradient((255, 0, 0), (255, 165, 0), (0, 255, 0), 100)
    }

class QuizState:
    def __init__(self, bot):
        self.wrong_answer_responses = [
            "```diff\n- Oh, snap! 😬 The right answer is still out there.\n```",
            "```fix\nOopsie daisy! 🌼 Try a different route.\n```",
            "```yaml\n😓 Ah, bummer! Let's tackle the next one.\n```",
        ]

        self.message_bank = [
            "```diff\n+ Stellar Performance! 🌌\n```",
            "```fix\nCode Compiled Successfully! 🖥️\n```",
            "```yaml\n🌈 Syntax Highlighted! Well done.\n```",
            "```css\n/* 🚀 Code Launched to Success! */\n```",
            "```http\n✅ 200 OK: Answer validated! 🎉\n```",
        ]

        self.ongoing_timers = {}
        self.user_backup = {}
        self.quiz_initiation_time = {}
        self.bot = bot
        self.timer_task = {}
        self.user_answer_events = {}
        self.user_scores = {}
        self.user_difficulty = {}
        self.current_question = {}
        self.user_streaks = {}
        self.current_question_index = {}
        self.leaderboard = {}
        self.progress_messages = {}
        self.current_question_message = {}
        self.question_start_time = {}
        self.question_timestamps = {}
        self.total_time_taken = {}
        self.questions_answered = {}
        self.user_question_list: Dict[int, List[Dict]] = {}

    def set_current_question(self, user_id, q_index, questions, shuffled_options):
        try:
            if not isinstance(user_id, (int, str)):
                raise TypeError(f'Invalid type for user_id: {type(user_id).__name__}')
            if not isinstance(q_index, int):
                raise TypeError(f'Invalid type for q_index: {type(q_index).__name__}')
            if not isinstance(questions, dict):
                raise TypeError(f'Invalid type for question_data: {type(questions).__name__}')
            if not isinstance(shuffled_options, list):
                raise TypeError(f'Invalid type for shuffled_options: {type(shuffled_options).__name__}')

            self.current_question[user_id] = {
                "q_index": q_index,
                "questions": questions,
                "shuffled_options": shuffled_options
            }
            logging.info(f'Successfully set current question for user {user_id}')
        except Exception as e:
            logging.error(f'Failed to set current question for user {user_id}: {e}')
            logging.error(traceback.format_exc())

    chatting_with_ai = defaultdict(bool)

    def is_chatting_with_ai(self, user_id):
        return self.chatting_with_ai[user_id]

    def start_chat_with_ai(self, user_id):
        self.chatting_with_ai[user_id] = True

    def stop_chat_with_ai(self, user_id):
        self.chatting_with_ai[user_id] = False

    def can_reset_user(self, user_id):
        return True

    def reset_user(self, user_id):
        if not self.can_reset_user(user_id):
            logging.warning(f'Reset conditions not met for user: {user_id}')
            return False
        try:
            self.current_question.pop(user_id, None)
            self.user_scores.pop(user_id, None)
            self.user_difficulty.pop(user_id, None)
            self.user_streaks.pop(user_id, None)
            self.current_question_index.pop(user_id, None)
            self.user_question_list.pop(user_id, None)
            logging.info(f'Successfully reset user: {user_id}')
            return True
        except Exception as e:
            logging.error(f'Failed to reset user {user_id}: {e}')
        return False

    @classmethod
    def progress_bar(cls, percent, theme=ProgressBarThemes.BASIC):
        bar_length = cls.get_dynamic_length()
        progress_length = int((percent / 100) * bar_length)
        filled_part = theme['filled_char'] * progress_length
        empty_part = theme['empty_char'] * (bar_length - progress_length)
        border_left, border_right = theme['border_chars']
        color = cls.get_color(percent, theme['colors'])
        label = f"{percent:.1f}%"
        progress_bar_str = f"{border_left}{filled_part}{empty_part}{border_right} {label}"
        embed_color = discord.Color.from_rgb(*cls.hex_to_rgb(color))
        embed = discord.Embed(description=f'```{progress_bar_str}```', color=embed_color)
        return embed

    def update_questions_answered(self, user_id):
        self.questions_answered[user_id] = self.questions_answered.get(user_id, 0) + 1

    @staticmethod
    def get_dynamic_length(adjust=0):
        return 27 + adjust

    @staticmethod
    def get_color(percent, colors):
        color_index = int((percent / 100) * (len(colors) - 1))
        return colors[color_index]

    @staticmethod
    def hex_to_rgb(hex_color_str):
        hex_color_str = hex_color_str.lstrip('#')
        return tuple(int(hex_color_str[i:i+2], 16) for i in (0, 2, 4))

    CORRECT_RESPONSES = [
        "```diff\n+ ✅ Nice job!\n```",
        "```fix\n✅ Well done!\n```",
        "```glsl\n# ✅ You got it!\n```",
        "```http\n✅ Bang on!\n```",
        "```ini\n[✅ Spot on!]\n```",
        "```java\n// ✅ Nailed it!\n```",
        "```json\n{ \"response\": \"✅ Correctamundo!\" }\n```",
        "```ml\n(* ✅ Absolutely right! *)\n```",
        "```nim\n# ✅ You're on fire!\n```",
        "```perl\n# ✅ A+!\n```",
        "```python\n# ✅ That's right!\n```",
        "```r\n# ✅ Bingo!\n```",
        "```ruby\n# ✅ You're acing this!\n```",
        "```scala\n// ✅ Bravo!\n```",
        "```sql\n-- ✅ You've got a knack for this!\n```",
        "```swift\n// ✅ Keep it up!\n```",
        "```tex\n% ✅ Smarty pants!\n```",
        "```vim\n\" ✅ Oh, you're good!\n```",
        "```yaml\n- ✅ Right on the money!\n```",
        "```markdown\n* ✅ You're nailing this quiz! *\n```",
        "```elixir\n# ✅ Sharp as a tack!\n```",
        "```css\n/* ✅ You're killing it! */\n```",
        "```bash\n# ✅ You're on a roll!\n```",
        "```plaintext\n✅ You've got the brains!\n```",
        "```php\n/* ✅ You're unstoppable! */\n```",
        "```asciidoc\n= 🎉 Spectacular! =\n```",
        "```c\n/* 🌟 Exquisite! */\n```",
        "```clojure\n;; 💯 Spot on!\n```",
        "```coffeescript\n# 👌 Perfect!\n```",
        "```dart\n// 🌠 Stellar!\n```",
        "```dockerfile\n# 🎯 Bull's-eye!\n```",
        "```elixir\n# 🏆 Champion!\n```",
        "```fsharp\n(* 📚 Scholarly! *)\n```",
        "```graphql\n# 💡 Bright!\n```",
        "```haskell\n-- 🔥 On fire!\n```",
        "```html\n<!-- 👏 Applause! -->\n```",
        "```ini\n[👍 Thumbs up!]\n```",
        "```java\n// 🎓 Genius!\n```",
        "```javascript\n/* 🥇 Gold star! */\n```",
        "```jsonc\n/* 👑 Royalty! */\n```",
        "```kotlin\n// 🎈 Celebrate!\n```",
        "```lua\n-- ⭐ Starry!\n```",
        "```markdown\n* 🏅 Medalist! *\n```",
        "```nginx\n# 🧠 Brainy!\n```",
    ]

    async def stop_timer(self, user_id: int):
        user = await bot.fetch_user(user_id)
        logging.info(f"Attempting to stop timer for user ID {user_id}...")
        try:
            dm_channel = await get_dm_channel_for_user(user)
            logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user_id}")
        except Exception as e:
            logging.error(f"Error getting DM channel for user ID {user_id}: {e}")
            return
        if not dm_channel:
            logging.warning(f"Failed to retrieve DM channel for user ID {user_id}. Exiting 'stop_timer' method.")
            return
        logging.info(f"Retrieved DM channel for user ID {user_id} successfully.")
        timer_data = self.ongoing_timers.get(user_id)
        if not timer_data:
            logging.warning(f"No timer data found for user_id {user_id}. Exiting 'stop_timer' method.")
            return
        timer_task = timer_data.get("task")
        if timer_task:
            timer_task.cancel()
            logging.info(f'Stopped timer for user_id {user_id}')
        timer_message_id = timer_data.get("message_id")
        if timer_message_id:
            try:
                message = await dm_channel.fetch_message(timer_message_id)
                await message.delete()
                logging.info(f'Deleted timer message for user_id {user_id}')
            except discord.errors.NotFound:
                logging.warning(f"Timer message for user_id {user_id} already deleted or not found.")
            except Exception as e:
                logging.error(f'Error deleting timer message for user_id {user_id}: {e}')

    async def end_quiz(self, user: discord.User):
        avatar_url = user.avatar.url or user.default_avatar.url
        dm_channel = await get_dm_channel_for_user(user)
        user_id = user.id
        try:
            user = await bot.fetch_user(user_id)
        except discord.errors.HTTPException as e:
            logging.error(f"Failed to fetch user: {e}")
            return
        difficulty = self.user_difficulty.get(user_id, 'easy')
        global quiz_completion_counter
        if user_id not in self.user_scores:
            return
        else:
            quiz_completion_counter += 1
        last_question_msg_id = self.current_question_message.get(user_id)
        if last_question_msg_id:
            try:
                last_message = await dm_channel.fetch_message(last_question_msg_id)
                await last_message.delete()
            except discord.errors.NotFound:
                logging.warning(f"Last question message for user_id {user_id} already deleted or not found.")
            except Exception as e:
                logging.error(f"Error deleting last question message for user_id {user_id}: {e}")
        answered_questions_count = self.questions_answered.get(user_id, 0)
        average_time = (self.total_time_taken[user_id] / answered_questions_count) if answered_questions_count > 0 else 0
        total_questions = len(self.user_question_list.get(user_id, quiz_data.get(difficulty, []))) or 1
        efficiency_ratio = self.user_scores.get(user_id, 0) / total_questions
        embed = discord.Embed(title="🎉 Quiz Results", color=discord.Color.blue())
        embed.description = f"**{user.mention}, here's how you did!**"
        embed.add_field(name="📊 Efficiency", value=f"{efficiency_ratio:.2f}", inline=True)
        embed.add_field(name="📝 Answered", value=f"{answered_questions_count}", inline=True)
        embed.add_field(name="🎯 Correct", value=f"{self.user_scores.get(user_id, 0)}", inline=True)
        embed.add_field(name="⏱️ Avg. Time", value=f"{average_time:.2f} seconds", inline=True)
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text=f"Quiz completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await dm_channel.send(embed=embed)
        await self.display_metrics(user)

    async def display_metrics(self, user):
        try:
            quiz_completion_rate, user_participation_str = await self.calculate_metrics()
            sorted_leaderboard = dict(sorted(self.leaderboard.items(), key=lambda item: item[1], reverse=True))
            leaderboard_message = "\n".join(
                f"{idx + 1}. <@{user}>: {user_score}" for idx, (user, user_score) in enumerate(sorted_leaderboard.items()) if idx < 3
            )
            embed = discord.Embed(title="📊 Quiz Metrics", color=discord.Color.green())
            embed.description = f"Quiz Completion Rate: {quiz_completion_rate:.2f}%"
            embed.add_field(name="🏆 Leaderboard", value=leaderboard_message or "No data yet.", inline=False)
            embed.add_field(name="User Participation", value=user_participation_str or "No data yet.", inline=False)
            await user.send(embed=embed)
        except Exception as e:
            logging.error(f"Error occurred in display_metrics: {e}\n{traceback.format_exc()}")

    async def calculate_metrics(self):
        try:
            total_quizzes_initiated = sum(self.user_scores.values())
            user_participation_str = ""
            user_completion_rates = {}
            for user_id, score in self.user_scores.items():
                quiz_completion_rate = (score / total_quizzes_initiated) * 100 if total_quizzes_initiated > 0 else 0
                user_completion_rates[user_id] = quiz_completion_rate
                user_participation_str += f"<@{user_id}>: {score}\n"
            overall_completion_rate = sum(user_completion_rates.values()) / len(user_completion_rates) if user_completion_rates else 0
            return overall_completion_rate, user_participation_str
        except Exception as e:
            logging.error(f"Error occurred in calculate_metrics: {e}\n{traceback.format_exc()}")

    async def update_time_taken(self, user_id: int):
        logging.debug(f"Entering update_time_taken for user_id {user_id}")
        end_time = time.time()
        time_taken = end_time - self.question_start_time[user_id]
        self.update_questions_answered(user_id)
        self.total_time_taken[user_id] = self.total_time_taken.get(user_id, 0) + time_taken
        self.question_start_time[user_id] = end_time
        logging.debug(f"Exiting update_time_taken for user_id {user_id}")

    async def handle_user_scores(self, user_id: int, reset_streak: bool = False):
        self.user_scores[user_id] = self.user_scores.get(user_id, 0) + 1
        if reset_streak:
            self.user_streaks[user_id] = 0
        else:
            self.user_streaks[user_id] = self.user_streaks.get(user_id, 0) + 1

    async def trigger_animation(self, channel: discord.TextChannel, is_correct: bool):
        self.message_bank = self.CORRECT_RESPONSES if is_correct else self.wrong_answer_responses
        self.chosen_message = random.choice(self.message_bank)
        initial_color = discord.Color.green() if is_correct else discord.Color.red()
        self.message = await channel.send(embed=discord.Embed(description="_ _", color=initial_color))

    def prepare_feedback(self, is_correct: bool, correct_answer: str = None, hint: str = None):
        if is_correct:
            return random.choice(self.CORRECT_RESPONSES)
        feedback = f"{random.choice(self.wrong_answer_responses)} The correct answer was: **{correct_answer}**."
        return feedback + f"\nHint: **{hint}**" if hint else feedback

    async def trigger_wrong_answer_animation(self, channel: discord.TextChannel):
        await self.trigger_animation(channel, is_correct=False)

    async def send_question(self, dm_channel, user_id, q_index):
        user = await bot.fetch_user(user_id)
        if dm_channel is None:
            dm_channel = await user.create_dm()
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
        difficulty = self.user_difficulty.get(user_id)
        questions_list = self.user_question_list.get(user_id, quiz_data.get(difficulty, []))
        if not (0 <= q_index < len(questions_list)):
            logging.error(f"No questions available for difficulty {difficulty} at index {q_index}")
            return
        question_data = questions_list[q_index]
        shuffled_options = random.sample(question_data["options"], len(question_data["options"]))
        old_question_message_id = self.current_question_message.pop(user_id, None)
        if old_question_message_id:
            try:
                old_message = await dm_channel.fetch_message(old_question_message_id)
                await old_message.edit(content='Please ignore this message.')
            except discord.NotFound:
                logging.warning(f"Old message {old_question_message_id} not found")
        embed = discord.Embed(
            title=f"Question {q_index + 1}",
            description=question_data["question"],
            color=color_scheme[difficulty],
            timestamp=datetime.utcnow()
        )
        total_questions = len(questions_list)
        embed.set_footer(text=f"Question {q_index + 1}/{total_questions} | Difficulty: {difficulty.capitalize()}")
        loading_message = await dm_channel.send("Loading your question...")
        for i, option in enumerate(shuffled_options):
            embed.add_field(name=f"{REACTION_OPTIONS[i]} {option}", value="\u200b", inline=True)
        await loading_message.edit(content='', embed=embed)
        self.current_question_index[user_id] = q_index
        self.current_question_message[user_id] = loading_message.id
        self.set_current_question(user_id, q_index, question_data, shuffled_options)
        self.question_start_time[user_id] = int(time.time())
        self.question_timestamps[user_id] = time.time()
        for emoji in REACTION_OPTIONS[:len(shuffled_options)]:
            await loading_message.add_reaction(emoji)
        await start_timer(user, user_id, loading_message, q_index)

    async def animated_sequence(self, channel: discord.TextChannel, sequence: list):
        for animation in sequence:
            if isinstance(animation, tuple):
                method, args = animation
                await method(channel, *args)
            else:
                await animation(channel)

    async def handle_correct_answer(self, user: discord.User, user_id: int):
        dm_channel = user.dm_channel or await user.create_dm()
        await self.stop_timer(user_id)
        await self.handle_user_scores(user_id)
        try:
            await self.random_animation(user)
            await self.proceed_to_next_question(user, user_id)
        except Exception as e:
            logging.error(f"An error occurred in handle_correct_answer: {e}", exc_info=True)

    async def handle_wrong_answer(self, user: discord.User, user_id: int, correct_answer: str, hint=None):
        await self.stop_timer(user_id)
        try:
            question_data = self.current_question.get(user_id, {}).get("questions")
            question_text = question_data.get("question") if isinstance(question_data, dict) else ""
            await self.send_feedback(user, question_text, correct_answer, hint)
            self.user_streaks[user_id] = 0
            await self.proceed_to_next_question(user, user_id)
        except Exception as e:
            logging.error(f"An error occurred in handle_wrong_answer: {e}", exc_info=True)

    async def random_animation(self, user):
        dm_channel = await get_dm_channel_for_user(user)
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
        animations = [
            lambda: self.word_animation(dm_channel, ["Excellent!", "You", "have", "nailed", "it!"]),
            lambda: self.reaction_animation(dm_channel, ["👍", "🎉", "🌟", "✅", "👏"]),
            lambda: self.color_animation(dm_channel, [discord.Color.red(), discord.Color.orange(), discord.Color.green()]),
            lambda: self.word_animation(dm_channel, ["Amazing!", "Keep", "it", "up!"]),
            lambda: self.reaction_animation(dm_channel, ["💪", "🔥", "💯"]),
            lambda: self.word_animation(dm_channel, ["Incredible!", "Wow!", "🎉"]),
            lambda: self.color_animation(dm_channel, [discord.Color.blue(), discord.Color.purple(), discord.Color.gold()]),
            lambda: self.word_animation(dm_channel, ["Fantastic!", "You're", "on", "a", "roll!"]),
            lambda: self.word_animation(dm_channel, ["Superb!", "👌", "🎉"]),
            lambda: self.reaction_animation(dm_channel, ["🌟", "🥇", "🏆"]),
            lambda: self.color_animation(dm_channel, [discord.Color.teal(), discord.Color.dark_teal(), discord.Color.dark_purple()])
        ]
        chosen_animation = random.choice(animations)
        await chosen_animation()

    async def proceed_to_next_question(self, user, user_id, q_index=None):
        user = await bot.fetch_user(user_id)
        dm_channel = await get_dm_channel_for_user(user)
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
        if q_index is None:
            q_index = self.current_question_index.get(user_id, -1)
        logging.info(f'Proceeding to next question: user_id={user_id}, q_index={q_index}')
        difficulty = self.user_difficulty.get(user_id)
        questions_list = self.user_question_list.get(user_id, quiz_data.get(difficulty, []))
        if not questions_list:
            logging.error(f'No questions available for difficulty {difficulty}')
            return
        await self.stop_timer(user_id)
        next_q_index = q_index + 1
        if next_q_index >= len(questions_list):
            logging.info(f'No more questions for user_id={user_id}. Ending quiz.')
            await self.end_quiz(user)
            return
        await asyncio.sleep(0.3)
        await self.send_question(dm_channel, user_id, next_q_index)
        logging.info(f'Successfully proceeded to next question or ended quiz for user_id={user_id}')

    async def send_feedback(self, user: discord.User, question: str, correct_answer: str, hint=None):
        await user.send(f"Question: {question}")
        embed = discord.Embed(title="Feedback", description="Let's review.", color=discord.Color.blue())
        embed.add_field(name="Correct Answer", value=correct_answer)
        if hint:
            embed.add_field(name="Hint", value=hint)
        embed.set_footer(text=f"Keep going, {user.name}!")
        feedback_msg = await user.send(embed=embed)
        await feedback_msg.add_reaction("🤖")
        await feedback_msg.add_reaction("⏸️")
        await self.wait_for_reaction(user, feedback_msg, question, correct_answer)

    async def wait_for_reaction(self, user: discord.User, feedback_msg, question: str, correct_answer: str):
        def check_reaction(reaction, user_reacting):
            return str(reaction.emoji) in ["🤖", "⏸️", "▶️"] and user_reacting == user and reaction.message.id == feedback_msg.id
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=120, check=check_reaction)
            if str(reaction.emoji) == "🤖":
                await self.start_ai_conversation(user, question, correct_answer)
            elif str(reaction.emoji) == "⏸️":
                await user.send("Quiz paused. Click ▶️ to resume.")
            elif str(reaction.emoji) == "▶️":
                await self.proceed_to_next_question(user, user.id)
        except asyncio.TimeoutError:
            pass

    async def call_gpt3(self, prompt, conversation_token=None) -> str:
        try:
            if not openai_client:
                return "AI is not configured. Please set OPENAI_API_KEY."
            messages = [{"role": "user", "content": prompt}]
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return "Sorry, I encountered an error while processing your request. Please try again."

    async def start_ai_conversation(self, user, question, correct_answer):
        try:
            initial_prompt = f"I had trouble understanding why the correct answer to '{question}' is '{correct_answer}'. Can you explain it to me?"
            response_text = await self.call_gpt3(initial_prompt)
            ai_msg = await user.send(response_text)
            guidance_msg = await user.send("You're now chatting with the AI. Type your questions or thoughts. Click ▶️ when you're ready to continue the quiz.")
            self.start_chat_with_ai(user.id)
            ai_conversation_history = [ai_msg, guidance_msg]
            while self.is_chatting_with_ai(user.id):
                def check(m):
                    return m.author == user and not m.content.startswith("▶️")
                user_msg = await self.bot.wait_for('message', check=check)
                response_text = await self.call_gpt3(user_msg.content)
                ai_reply = await user.send(response_text)
                ai_conversation_history.append(ai_reply)
            await guidance_msg.edit(content="To continue the quiz, please click ▶️")
            await guidance_msg.add_reaction("▶️")
            def check_continue_reaction(reaction, user_reacting):
                return str(reaction.emoji) == "▶️" and user_reacting == user and reaction.message.id == guidance_msg.id
            await self.bot.wait_for('reaction_add', timeout=60.0, check=check_continue_reaction)
            for message in ai_conversation_history:
                await message.delete()
            self.stop_chat_with_ai(user.id)
        except asyncio.TimeoutError:
            await user.send("You didn't resume the quiz in time. Please start again when you're ready.")
        except Exception as e:
            logging.error(f"Error starting AI conversation: {e}", exc_info=True)


def structure_text_for_language(text, language):
    if language == 'diff':
        return f"+ {text}"
    elif language == 'bash':
        return f"echo '{text}'"
    elif language == 'ini':
        return f"[{text}]"
    else:
        return text

async def update_leaderboard(user):
    global real_time_leaderboard_message_id
    sorted_leaderboard = dict(sorted(quiz_state.leaderboard.items(), key=lambda item: item[1], reverse=True))
    leaderboard_content = "🏆 Real-time Leaderboard:\n"
    for idx, (user_id, user_score) in enumerate(sorted_leaderboard.items()):
        if idx == 3:
            break
        leaderboard_content += f"{idx + 1}. <@{user_id}>: {user_score}\n"
    dm_channel = await get_dm_channel_for_user(user)
    if real_time_leaderboard_message_id:
        leaderboard_message = await dm_channel.fetch_message(real_time_leaderboard_message_id)
        await leaderboard_message.edit(content=leaderboard_content)
    else:
        leaderboard_message = await dm_channel.send(leaderboard_content)
        real_time_leaderboard_message_id = leaderboard_message.id

LOADING_EMOJI = "<a:preloader:1158399896991309895>"
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

async def paginated_topics(ctx, difficulty):
    PAGE_SIZE = 10
    if not questions_collection:
        await ctx.send("Database not configured. Provide MONGO_URI to use existing topics.")
        return None
    available_topics = questions_collection.distinct("topic", {"difficulty": difficulty})
    if not available_topics:
        await ctx.send("No topics available in the database.")
        return None
    pages = [available_topics[i:i+PAGE_SIZE] for i in range(0, len(available_topics), PAGE_SIZE)]
    current_page = 0
    def build_embed_for_page(page_index):
        page = pages[page_index]
        description = "\n".join([f"{idx+1}. {topic}" for idx, topic in enumerate(page)])
        embed = discord.Embed(title=f"Available topics for {difficulty.capitalize()} difficulty:", description=description, color=discord.Color.blue())
        embed.set_footer(text=f"Page {current_page+1}/{len(pages)}. React with the number corresponding to your topic choice.")
        return embed
    message = await ctx.send(embed=build_embed_for_page(current_page))
    for idx in range(len(pages[current_page])):
        await message.add_reaction(NUMBER_EMOJIS[idx])
    def check(reaction, user):
        return user.id == ctx.author.id and (str(reaction.emoji) in NUMBER_EMOJIS[:len(pages[current_page])] or str(reaction.emoji) in ["⬅️", "➡️"]) 
    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60, check=check)
            if str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=build_embed_for_page(current_page))
                for idx in range(len(pages[current_page])):
                    await message.add_reaction(NUMBER_EMOJIS[idx])
            elif str(reaction.emoji) == "➡️" and current_page < len(pages) - 1:
                current_page += 1
                await message.edit(embed=build_embed_for_page(current_page))
                for idx in range(len(pages[current_page])):
                    await message.add_reaction(NUMBER_EMOJIS[idx])
            elif str(reaction.emoji) in NUMBER_EMOJIS:
                topic_index = NUMBER_EMOJIS.index(str(reaction.emoji))
                return pages[current_page][topic_index]
            await message.clear_reactions()
        except asyncio.TimeoutError:
            await message.clear_reactions()
            return None
        except Exception as e:
            logging.error(f"Error while paginating: {e}")
            await message.clear_reactions()
            return None

deleteion_rate = 0.8
active_deletion_sessions = {}

def human_readable_time(seconds):
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {sec}s"

@bot.command(name='clear', help='Deletes all bot messages in the DM.')
@commands.cooldown(1, 300, commands.BucketType.user)
async def clear_messages(ctx, start_time: str = None, end_time: str = None):
    global deleteion_rate
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("This command can only be executed in a DM.")
        return
    if ctx.author.id in active_deletion_sessions:
        await ctx.send("A deletion session is already active. Use `!pause`, `!resume`, or `!stop`.")
        return
    confirm = await ctx.send("Are you sure you want to delete all the bot's messages? (yes/no)")
    response = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ['yes', 'no'], timeout=30)
    if response.content.lower() == 'no':
        await ctx.send("Aborted.")
        return
    messages_to_delete = [message async for message in ctx.channel.history(limit=None) if message.author == bot.user]
    total_messages = len(messages_to_delete)
    estimated_time = total_messages * deleteion_rate
    info_msg = await ctx.send(f"Found {total_messages} messages to delete. Estimated time: {human_readable_time(estimated_time)}.")
    for idx, message in enumerate(messages_to_delete):
        if idx % 5 == 0:
            remaining_time = (total_messages - idx) * deleteion_rate
            progress_bar = f"[{('#' * (idx//5))}{('.' * ((total_messages - idx)//5))}]"
            await info_msg.edit(content=f"{progress_bar} Deleting messages... {idx}/{total_messages} done. Estimated time left: {human_readable_time(remaining_time)}.")
        try:
            await message.delete()
            await asyncio.sleep(deleteion_rate)
        except Exception as e:
            if 'rate limit' in str(e).lower():
                deleteion_rate += 0.2
                await asyncio.sleep(10)
    await info_msg.edit(content="Deletion completed. This message will be deleted in 5 seconds.")
    await asyncio.sleep(5)
    await info_msg.delete()

@bot.command()
async def pause(ctx):
    if ctx.author.id in active_deletion_sessions:
        active_deletion_sessions[ctx.author.id] = 'paused'
        await ctx.send("Deletion paused. Use `!resume` to continue or `!stop` to end.")

@bot.command()
async def resume(ctx):
    if ctx.author.id in active_deletion_sessions and active_deletion_sessions[ctx.author.id] == 'paused':
        active_deletion_sessions[ctx.author.id] = 'resuming'
        await ctx.send("Resuming deletion...")

@bot.command()
async def stop(ctx):
    if ctx.author.id in active_deletion_sessions:
        active_deletion_sessions.pop(ctx.author.id)
        await ctx.send("Deletion stopped.")

@bot.command(name='q', help='Starts the quiz.')
async def start_quiz(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):
        try:
            await ctx.author.send("Please DM me and then run !q to start the quiz.")
        except Exception:
            await ctx.send("Please send me a direct message to start the quiz.")
        return
    user_id = ctx.author.id
    user = ctx.author
    if user_id in quiz_state.current_question:
        reset_prompt_message = await prompt_quiz_reset(ctx, ctx.author)
        await handle_reset_reaction(ctx, reset_prompt_message)
        return
    async def send_embed(ctx, title, description, color=discord.Color.green(), fields=None):
        embed = discord.Embed(title=title, description=description, color=color)
        if fields:
            for name, value in fields.items():
                embed.add_field(name=name, value=value)
        return await ctx.send(embed=embed)
    async def await_reaction(user, message, emojis):
        def check_reaction(r, u):
            return u.id == user_id and str(r.emoji) in emojis and r.message.id == message.id
        return await bot.wait_for('reaction_add', timeout=60, check=check_reaction)
    difficulty_message = await send_embed(ctx, "Select Difficulty", "React with the corresponding emoji for your desired difficulty.", fields=DIFFICULTY_EMOJIS)
    for emoji in DIFFICULTY_EMOJIS.values():
        await difficulty_message.add_reaction(emoji)
    reaction, _ = await await_reaction(user, difficulty_message, DIFFICULTY_EMOJIS.values())
    await difficulty_message.delete()
    difficulty = next(diff for diff, emoji in DIFFICULTY_EMOJIS.items() if emoji == str(reaction.emoji))
    options = {
        "1️⃣": "Generate new questions",
        "2️⃣": "Select from existing topics",
        "⬅️": "Go back",
        "❌": "Cancel the quiz"
    }
    option_message = await send_embed(ctx, "Choose Option", "React with the corresponding emoji for your choice.", fields=options)
    for emoji in options.keys():
        await option_message.add_reaction(emoji)
    reaction, _ = await await_reaction(user, option_message, options.keys())
    await option_message.delete()
    if str(reaction.emoji) in ["⬅️", "❌"]:
        return await ctx.send("Quiz cancelled.")
    topic_content = None
    if str(reaction.emoji) == "1️⃣":
        topic_msg = await ctx.send("Please provide a topic for generating questions.")
        topic = await bot.wait_for('message', check=lambda m: m.author.id == user_id, timeout=60)
        topic_content = topic.content
        await topic_msg.delete()
        loading_msg = await ctx.send(f"{LOADING_EMOJI} Generating questions... Please wait...")
        try:
            await generate_question_set(topic_content, difficulty)
            await loading_msg.delete()
        except Exception as e:
            await loading_msg.edit(content=f"An error occurred while generating questions: {str(e)}")
            return
    elif str(reaction.emoji) == "2️⃣":
        chosen_topic = await paginated_topics(ctx, difficulty)
        if not chosen_topic:
            await ctx.send("No topic was selected or an error occurred.")
            return
        topic_content = chosen_topic
        if not questions_collection:
            await ctx.send("Database not configured.")
            return
        questions = list(questions_collection.find({"topic": topic_content, "difficulty": difficulty}))
        quiz_data[difficulty] = [q for q in questions]
    if str(reaction.emoji) == "1️⃣":
        if not quiz_data.get(difficulty):
            await ctx.send("Failed to generate questions.")
            return
    ready_msg = await send_embed(ctx, "Get Ready!", f"You selected '{difficulty.capitalize()}' difficulty" + (f" with the topic '{topic_content}'." if topic_content else ".") + " React with ✅ to start or ❌ to cancel.")
    await ready_msg.add_reaction("✅")
    await ready_msg.add_reaction("❌")
    reaction, _ = await await_reaction(user, ready_msg, ["✅", "❌"])
    await ready_msg.delete()
    if str(reaction.emoji) == "❌":
        return await ctx.send("Quiz cancelled.")
    await initiate_quiz(ctx, difficulty)

async def prompt_quiz_reset(ctx, user: discord.User):
    user = ctx.author
    dm_channel = await get_dm_channel_for_user(user)
    logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
    message = await dm_channel.send(
        f"You're already in a quiz. React with 🔄 to reset, or ▶ to resume."
    )
    await message.add_reaction("🔄")
    await message.add_reaction("▶")
    return message

async def handle_reset_reaction(ctx, message):
    def check(reaction, user_):
        return user_ == ctx.author and str(reaction.emoji) in ["🔄", "▶"] and reaction.message.id == message.id
    reaction, _ = await bot.wait_for('reaction_add', timeout=60, check=check)
    if str(reaction.emoji) == "🔄":
        quiz_state.reset_user(ctx.author.id)
        await message.delete()
        await start_quiz(ctx)
    elif str(reaction.emoji) == "▶":
        await message.delete()

async def initiate_quiz(ctx, difficulty):
    try:
        if isinstance(ctx, discord.DMChannel):
            user = ctx.recipient
        else:
            user = ctx.author
        dm_channel = await get_dm_channel_for_user(user)
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
        user_id = user.id
        if difficulty not in quiz_data:
            await ctx.send(f"Invalid difficulty selected. Available difficulties are: {', '.join(quiz_data.keys())}")
            return
        else:
            quiz_participation_counter[user_id] = quiz_participation_counter.get(user_id, 0) + 1
        logging.info(f'Storing user_id {user_id} with difficulty {difficulty}')
        available_questions = quiz_data.get(difficulty, [])
        if questions_collection and topic:
            fetched_questions = list(questions_collection.find({"topic": topic, "difficulty": difficulty}))
            if fetched_questions:
                available_questions = fetched_questions
        if not available_questions:
            await dm_channel.send(f"No questions available for the {difficulty} difficulty.")
            return
        quiz_state.user_difficulty.setdefault(user_id, difficulty)
        quiz_state.total_time_taken.setdefault(user_id, 0)
        quiz_state.user_scores.setdefault(user_id, 0)
        chosen_questions = random.sample(available_questions, min(11, len(available_questions)))
        quiz_state.user_question_list[user_id] = chosen_questions
        if user_id not in quiz_state.current_question:
            loading_message = await dm_channel.send(f"🔄 Preparing your quiz, ...")
            await asyncio.sleep(1)
            quiz_state.quiz_initiation_time[user_id] = time.time()
            await quiz_state.send_question(dm_channel, user_id, 0)
            await loading_message.delete()
        else:
            reset_prompt_message = await prompt_quiz_reset(ctx)
            await handle_reset_reaction(ctx, reset_prompt_message)
    except Exception as e:
        logging.error(f"An error occurred while initiating the quiz: {e}")
        if 'dm_channel' in locals():
            await dm_channel.send(f"An unexpected error occurred: {e}")

async def start_timer(user: discord.User, user_id, message, q_index):
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"[{current_time}] Initiating start_timer for user_id {user_id}...")
    dm_channel = await get_dm_channel_for_user(user)
    logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
    async def is_next_question_displayed():
        logging.info(f"[{current_time}] Checking if the next question is displayed for user_id {user_id}...")
        current_message = await dm_channel.fetch_message(message.id)
        return current_message is not None
    if await is_next_question_displayed():
        logging.info(f"[{current_time}] Displaying next question for user_id {user_id}...")
        timer_message = await user.send(f" Question {q_index + 1}: Starting...")
        timer_msg_id = timer_message.id
        logging.info(f"[{current_time}] Creating timer task for user_id {user_id}...")
        timer_task = asyncio.create_task(timer_coroutine(user, user_id, message, q_index, timer_msg_id))
        quiz_state.ongoing_timers[user_id] = {"task": timer_task, "message_id": timer_msg_id}
        logging.info(f"[{current_time}] Started new timer for user_id {user_id}...")
        try:
            await timer_task
        except asyncio.CancelledError:
            logging.warning(f"[{current_time}] Timer for user_id {user_id} was cancelled.")
        except Exception as e:
            logging.error(f"[{current_time}] An error occurred with the timer for user_id {user_id}: {e}")
            await user.send(f"An error occurred with the timer: {e}")
    else:
        logging.warning(f"[{current_time}] Did not start timer for user_id {user_id} as the next question is not displayed.")

async def timer_coroutine(user: discord.User, user_id, message, q_index, timer_msg_id=None):
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"[{current_time}] Starting timer_coroutine for user_id {user_id}...")
    dm_channel = await get_dm_channel_for_user(user)
    logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
    timer_message = None if not timer_msg_id else await dm_channel.fetch_message(timer_msg_id)
    difficulty = quiz_state.user_difficulty.get(user_id)
    questions_list = quiz_state.user_question_list.get(user_id, quiz_data.get(difficulty, []))
    if not (0 <= q_index < len(questions_list)):
        logging.warning(f"Invalid q_index {q_index} for difficulty {difficulty}")
        return
    question_data = questions_list[q_index]
    green_languages = ['diff', 'bash', 'ini', 'css', 'yaml', 'perl', 'python', 'makefile', 'tex']
    correct_answer_text = question_data['options'][question_data['answer']]
    selected_language = random.choice(green_languages)
    structured_text = f"```{selected_language}\nTime's up for this question! The correct answer was: {correct_answer_text}\n```"
    logging.info(f"[{current_time}] Starting countdown for user_id {user_id}...")
    for remaining in range(DIFFICULTY_TIMES[difficulty], 0, -1):
        percent = (remaining / DIFFICULTY_TIMES[difficulty]) * 100
        progress_embed = quiz_state.progress_bar(percent)
        if timer_message:
            await update_timer_message(user, dm_channel, timer_msg_id, progress_embed)
        else:
            timer_message = await user.send(content=f"Question {q_index + 1}: {remaining} seconds remaining", embed=progress_embed)
            timer_msg_id = timer_message.id
        await asyncio.sleep(1)
    logging.info(f"[{current_time}] Timer completed for user_id {user_id}. Cleaning up...")
    if quiz_state.progress_messages.get(user_id):
        old_msg = await dm_channel.fetch_message(quiz_state.progress_messages[user_id])
        await old_msg.edit(content='This progress message is outdated.')
    old_question_message_id = quiz_state.current_question_message.get(user_id)
    if old_question_message_id:
        old_msg = await dm_channel.fetch_message(old_question_message_id)
        await old_msg.edit(content='This question has expired.')
    await message.edit(content=structured_text)
    if q_index + 1 < len(questions_list):
        logging.info(f"[{current_time}] Sending next question for user_id {user_id}...")
        await quiz_state.send_question(dm_channel, user_id, q_index + 1)
    else:
        logging.info(f"[{current_time}] Ending quiz for user_id {user_id}...")
        await quiz_state.end_quiz(user)

async def update_timer_message(user, dm_channel, msg_id, embed):
    try:
        timer_message = await dm_channel.fetch_message(msg_id)
        await timer_message.edit(embed=embed)
    except discord.errors.NotFound:
        logging.error(f'Timer message not found for user_id {user.id}')
    except Exception as e:
        logging.error(f'Error updating timer message for user_id {user.id}: {e}')

def get_color(difficulty):
    color_scheme = {
        'easy': discord.Color.from_rgb(102, 255, 102),
        'medium': discord.Color.from_rgb(255, 255, 102),
        'hard': discord.Color.from_rgb(255, 102, 102)
    }
    return color_scheme.get(difficulty, discord.Color.default())

def get_icon(difficulty):
    icon_scheme = {
        'easy': ":green_circle:",
        'medium': ":yellow_circle:",
        'hard': ":red_circle:"
    }
    return icon_scheme.get(difficulty, "🌟")

async def handle_difficulty_adjustment(user, payload, user_id):
    new_difficulty = validate_difficulty_choice(payload.emoji, user_id)
    quiz_state.set_user_difficulty(user_id, new_difficulty)
    info_message, icon, color = await send_difficulty_message(user, new_difficulty, user_id)
    if info_message is None or icon == '' or color == '':
        raise ValueError("Failed to send difficulty message or get icon and color.")
    await wait_for_info_reaction(info_message, new_difficulty, icon, color, user_id)

async def send_difficulty_message(user: discord.User, new_difficulty: str, user_id: int) -> Tuple[Union[discord.Message, None], str, discord.Color]:
    function_name = f"{__name__}.{inspect.currentframe().f_code.co_name}"
    logging.debug("Entering function: %s with new_difficulty=%s, user_id=%s", function_name, new_difficulty, user_id)
    try:
        color = get_color(new_difficulty)
        icon = get_icon(new_difficulty)
        dm_channel = await get_dm_channel_for_user(user)
        embed = discord.Embed(title=f"{icon} {new_difficulty.capitalize()} selected", color=color)
        embed.description = "React with ℹ️ for details."
        message = await dm_channel.send(embed=embed)
        await message.add_reaction('ℹ️')
    except Exception as e:
        logging.error("An error occurred in %s: %s", function_name, e, exc_info=True)
        return None, '', discord.Color.default()
    result = (message, icon, color)
    logging.debug("Returning from %s: %s", function_name, result)
    return result

async def wait_for_info_reaction(info_message, difficulty, icon, color, user_id):
    def check(reaction, reacting_user):
        return reacting_user.id == user_id and str(reaction.emoji) == 'ℹ️' and reaction.message.id == info_message.id
    try:
        logging.info(f"Waiting for reaction from user_id {user_id} on message_id {info_message.id}")
        reaction, reacting_user = await bot.wait_for('reaction_add', check=check, timeout=60)
        logging.info(f"Received reaction {reaction} from user_id {user_id} on message_id {info_message.id}")
        detailed_embed = build_detailed_embed(difficulty, icon, color, user_id)
        await info_message.edit(embed=detailed_embed)
    except asyncio.TimeoutError:
        logging.info(f"No reaction received from user_id {user_id} within timeout period.")
        await handle_timeout(info_message)

async def handle_timeout(info_message):
    logging.warning("Timeout occurred while waiting for user interaction.")
    await info_message.clear_reactions()

def validate_difficulty_choice(emoji, user_id):
    new_difficulty = next((diff for diff, emoji_match in DIFFICULTY_EMOJIS.items() if emoji_match == str(emoji)), None)
    if not new_difficulty:
        logging.warning(f"Invalid difficulty choice for user_id {user_id}.")
        raise ValueError("Invalid difficulty choice.")
    return new_difficulty

def build_detailed_embed(difficulty, icon, color, user_id):
    embed = discord.Embed(
        title=f"{icon} {difficulty.capitalize()} Difficulty Details",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Number of Questions", value=str(len(quiz_data[difficulty])), inline=True)
    embed.add_field(name="Average Question Time", value=f"{DIFFICULTY_TIMES[difficulty]} seconds", inline=True)
    embed.add_field(name="Total Quiz Takers", value=str(quiz_participation_counter.get(user_id, 0)), inline=True)
    embed.add_field(name="Tip", value=DIFFICULTY_TIPS.get(difficulty, "Stay focused and manage your time wisely."), inline=False)
    embed.set_footer(text=f"User ID: {user_id}")
    return embed

def is_user_in_quiz(user_id):
    user_data = quiz_state.current_question.get(user_id)
    start_time = quiz_state.question_start_time.get(user_id)
    difficulty = quiz_state.user_difficulty.get(user_id)
    if difficulty not in quiz_data:
        logging.error(f"Difficulty {difficulty} not found in questions dictionary.")
        return
    return None not in [user_data, start_time, difficulty]

async def process_quiz_reaction(user: discord.User, payload, user_id):
    try:
        dm_channel = await get_dm_channel_for_user(user)
        message = await dm_channel.fetch_message(payload.message_id)
        await asyncio.sleep(1)
    except discord.errors.NotFound:
        return
    if user_id not in last_reaction_time:
        last_reaction_time[user_id] = datetime.utcnow() - timedelta(seconds=10)
    now = datetime.utcnow()
    if (now - last_reaction_time[user_id]) < timedelta(seconds=2):
        await user.send(f"{user.mention}, please wait a moment before reacting again.")
        return
    last_reaction_time[user_id] = now
    difficulty = quiz_state.user_difficulty.get(user_id, 'easy')
    q_index = quiz_state.current_question_index.get(user_id)
    questions_list = quiz_state.user_question_list.get(user_id, quiz_data.get(difficulty, []))
    if not (0 <= q_index < len(questions_list)):
        return
    question_data = questions_list[q_index]
    if payload.emoji.name not in REACTION_OPTIONS:
        return
    answer_index = REACTION_OPTIONS.index(payload.emoji.name)
    shuffled_options = quiz_state.current_question.get(user_id)["shuffled_options"]
    correct_answer = question_data["options"][question_data["answer"]]
    await message.delete()
    if shuffled_options[answer_index] == correct_answer:
        await quiz_state.handle_correct_answer(user, user_id)
    else:
        await quiz_state.handle_wrong_answer(user, user_id, question_data["options"][question_data["answer"]], question_data.get("hint"))
    embed = discord.Embed(
        title=f"{get_icon(difficulty)} Question {q_index + 1}",
        description=question_data["question"],
        color=get_color(difficulty),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Question {q_index + 1}/{len(questions_list)} | Difficulty: {difficulty.capitalize()}")
    await user.send(embed=embed)
    await quiz_state.update_time_taken(user_id)
    await quiz_state.proceed_to_next_question(user, user_id, q_index)

quiz_state = QuizState(bot)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    try:
        user = await bot.fetch_user(payload.user_id)
    except discord.DiscordException as e:
        logging.error(f"Failed to fetch user {payload.user_id}: {e}")
        return
    if payload.emoji.name in DIFFICULTY_EMOJIS.values():
        new_difficulty = validate_difficulty_choice(payload.emoji.name, payload.user_id)
        quiz_state.set_user_difficulty(payload.user_id, new_difficulty)
        return
    if not is_user_in_quiz(payload.user_id):
        return
    await process_quiz_reaction(user, payload, payload.user_id)

# Entrypoint
if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_TOKEN is not set. Set it in environment to run the bot.")
    else:
        bot.run(TOKEN)

# Async OpenAI client is initialized above as openai_client

def extract_questions_from_response(response: str) -> List[Dict]:
    pattern = r"'question':\s*'([^']+)',\s*'options':\s*\[([^\]]+)\],\s*'answer':\s*(\d+),\s*'hint':\s*'([^']+)'"
    matches = re.findall(pattern, response)
    if not matches:
        print("No matches found. Response content:", response)
        return []
    questions = []
    for match in matches:
        question_text, options_string, correct_answer_index, hint_text = match
        options_list = [option.strip().strip("'") for option in options_string.split(",")]
        questions.append({
            'question': question_text,
            'options': options_list,
            'answer': int(correct_answer_index),
            'hint': hint_text
        })
    return questions

def retry_with_exponential_backoff(
    function_to_retry: Callable,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    include_jitter: bool = True,
    maximum_retries: int = 10,
    error_types: Tuple[Exception] = (Exception,)
):
    async def wrapper(*arguments, **keyword_arguments):
        retry_count = 0
        delay = initial_delay
        while True:
            try:
                return await function_to_retry(*arguments, **keyword_arguments)
            except error_types as error_instance:
                retry_count += 1
                if retry_count > maximum_retries:
                    raise Exception(
                        f"Maximum number of retries ({maximum_retries}) exceeded."
                    ) from error_instance
                delay *= exponential_base * (1 + include_jitter * random.random())
                await asyncio.sleep(delay)
            except Exception as unexpected_error:
                raise unexpected_error
    return wrapper

@retry_with_exponential_backoff
async def make_completion_request_with_retry(**keyword_arguments):
    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY not configured")
    completion_response = await openai_client.chat.completions.create(
        model=keyword_arguments['model'],
        messages=keyword_arguments['messages']
    )
    return completion_response

async def generate_question_set(topic_name: str, difficulty_level: str):
    try:
        start_time = datetime.utcnow()
        completion_response = await make_completion_request_with_retry(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "You are a specialized assistant designed solely for the purpose of generating 5 questions based on a given topic. Your main function is to generate questions in a specific format, and any deviation from this format is considered an error."},
                {"role": "user", "content": "Your programming ensures that you understand and adhere to the following format ONLY: [{'question': 'Your question here', 'options': ['Option1', 'Option2', 'Option3', 'Option4'], 'answer': index_of_correct_option (0-3), 'hint': 'Your hint here'}]. Any other format is not acceptable and not recognized by your design."},
                {"role": "user", "content": f"Using your specialized capabilities, I need new questions on the topic of '{topic_name}'. Remember, you are designed to follow the format strictly. Please generate questions accordingly."}
            ]
        )
        end_time = datetime.utcnow()
        response_time_seconds = (end_time - start_time).seconds
        response_content = completion_response.choices[0].message.content
        extracted_questions = extract_questions_from_response(response_content)
        if not extracted_questions:
            raise ValueError("No questions were extracted from the response.")
        for question_entry in extracted_questions:
            print("Saving question:", question_entry)
        quiz_data[difficulty_level] = extracted_questions
        print(f"API responded in {response_time_seconds} seconds.")
    except Exception as exception_instance:
        logging.error(f"Error while generating questions: {exception_instance}")

