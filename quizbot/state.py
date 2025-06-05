import asyncio
import logging
import random
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Union
import discord
from .utils import get_dm_channel_for_user

last_reaction_time = defaultdict(lambda: datetime.utcnow())
color_scheme = {
    'easy': discord.Color.from_rgb(102, 255, 102),
    'medium': discord.Color.from_rgb(255, 255, 102),
    'hard': discord.Color.from_rgb(255, 102, 102)
}


class ProgressBarThemes:
    @staticmethod
    def generate_gradient(start, middle, end, steps):
        """Generate a gradient from start color to middle color to end color with a given number of steps."""
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

### Message Bank (Correct Responses):

        self.message_bank = [
            "```diff\n+ Stellar Performance! 🌌\n```",
            "```fix\nCode Compiled Successfully! 🖥️\n```",
            "```yaml\n🌈 Syntax Highlighted! Well done.\n```",
            "```css\n/* 🚀 Code Launched to Success! */\n```",
            "```http\n✅ 200 OK: Answer validated! 🎉\n```",
]

        
        self.ongoing_timers = {}  # Moved the ongoing_timers dictionary here
        self.user_backup = {}
        self.quiz_initiation_time = {}  # Add this line to define the quiz_initiation_time attribute
        
        self.bot = bot
        self.timer_task = {}
        self.user_answer_events = {} 
        self.user_scores = {}
        self.user_difficulty = {}
        # Dictionary to store current question data for each user question
        self.current_question = {}
        self.user_streaks = {}  #
        self.current_question_index = {}  # New property
        self.leaderboard = {}
        self.progress_messages = {}
        self.current_question_message = {}
        self.question_start_time = {}  # Store the start time of each question
        self.question_timestamps = {}  # Stores the timestamp when each question is sent
        self.total_time_taken = {}  # Stores the total time taken to answer questions
        
        self.questions_answered = {}  
    
    def set_current_question(self, user_id, q_index, questions, shuffled_options):
        try:
            # Type checking
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
            if user_id in self.current_question:
                logging.error(f'q_index: {q_index}, Total Questions: {len(self.current_question[user_id])}')
            else:
                logging.error(f'q_index: {q_index}, user_id {user_id} not found in current_question.')


    chatting_with_ai = defaultdict(bool)

    def is_chatting_with_ai(self, user_id):
        return self.chatting_with_ai[user_id]

    def start_chat_with_ai(self, user_id):
        self.chatting_with_ai[user_id] = True

    def stop_chat_with_ai(self, user_id):
        self.chatting_with_ai[user_id] = False

    
    def can_reset_user(self, user_id):
    

        """
        Check conditions under which a user reset is allowed.
    
        You can add conditions like:
        - If the user hasn't answered a question in a long time
        - If the user explicitly requested a reset
        - etc.
    
        Returns:
            bool: True if user can be reset, False otherwise.
        """
        # Add your conditions here
        return True  # Allow reset by default

    def reset_user(self, user_id):
        """
        Reset the user data if the conditions are met.
    
        Args:
            user_id: The ID of the user to reset.
    
        Returns:
            bool: True if the reset was successful, False otherwise.
        """
        if not self.can_reset_user(user_id):
            logging.warning(f'Reset conditions not met for user: {user_id}')
            return False  # Do not reset if conditions are not met

        try:
            self.current_question.pop(user_id, None)
            self.user_scores.pop(user_id, None)
            self.user_difficulty.pop(user_id, None)
            logging.info(f'Successfully reset user: {user_id}')
            return True  # Reset was successful

        except KeyError as ke:
            logging.error(f'Failed to reset user {user_id} due to KeyError: {ke}')
        except Exception as e:
            logging.error(f'Failed to reset user {user_id}: {e}')
        return False  # An error occurred, return False
        


    

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
        """Get dynamic length based on some condition or adjustment."""
        return 27 + adjust  # Static length of 25 with adjustment

    @staticmethod
    def get_color(percent, colors):
        """Get color based on the percentage progress."""
        color_index = int((percent / 100) * (len(colors) - 1))
        return colors[color_index]

    @staticmethod
    def hex_to_rgb(hex_color_str):
        hex_color_str = hex_color_str.lstrip('#')
        return tuple(int(hex_color_str[i:i+2], 16) for i in (0, 2, 4))

    
    
    



    CORRECT_RESPONSES = {
    1: [
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
        # ... And more
    ]
}







    wrong_answer_responses_RESPONSES = [
    "```diff\n- ❌ Oops! Better luck next time.\n```",
    "```fix\n❌ That's not right. Try again!\n```",
    "```glsl\n# ❌ Not quite right. Keep going!\n```",
    "```http\n❌ Missed it by that much.\n```",
    "```ini\n[❌ Oh, so close!]\n```",
    "```java\n// ❌ That's not the answer we were looking for.\n```",
    "```json\n{ \"response\": \"❌ You'll get it next time!\" }\n```",
    "```ml\n(* ❌ Don't let that stop you. *)\n```",
    "```nim\n# ❌ Keep trying, you'll get it!\n```",
    "```perl\n# ❌ Don’t sweat it, practice makes perfect!\n```",
    "```python\n# ❌ Remember, wrong answers are stepping stones to the right answer.\n```",
    "```r\n# ❌ Oops, that one slipped away.\n```",
    "```ruby\n# ❌ Oh dear, that's not right.\n```",
    "```scala\n// ❌ Don’t let this bump in the road stop you.\n```",
    "```sql\n-- ❌ Oh, tough luck.\n```",
    "```swift\n// ❌ That was a tricky one.\n```",
    "```tex\n% ❌ Ah, don’t let it get to you!\n```",
    "```vim\n\" ❌ Missed it by a hair.\n```",
    "```yaml\n- ❌ So close, yet so far.\n```",
    "```markdown\n* ❌ Keep your chin up, you’ll get the next one! *\n```",
    "```elixir\n# ❌ A minor setback for a major comeback!\n```",
    "```css\n/* ❌ A stumble may prevent a fall! */\n```",
    "```bash\n# ❌ Every mistake is a learning experience.\n```",
    "```plaintext\n❌ The path to success is filled with wrong turns.\n```",
    "```php\n/* ❌ The secret of getting ahead is getting started. */\n```",
    "```asciidoc\n= 🎭 Ah, a plot twist! =\n```",
    "```c\n/* 🙈 That answer was in disguise! */\n```",
    "```clojure\n;; 💼 It’s not in the bag yet!\n```",
    "```coffeescript\n# 👓 Needs a closer look!\n```",
    "```dart\n// 🎩 Not the magic word!\n```",
    "```dockerfile\n# 🐾 A little off the trail!\n```",
    "```elixir\n# 🌈 Not the pot of gold!\n```",
    "```fsharp\n(* 🚀 A little off orbit! *)\n```",
    "```graphql\n# 💫 Not quite star-studded!\n```",
    "```haskell\n-- 🎨 Needs a different stroke!\n```",
    "```html\n<!-- 🤔 That answer has wandered off! -->\n```",
    "```ini\n[🧩 Not the right fit, but keep piecing it together!]\n```",
    "```java\n// 🔍 A little more sleuthing required!\n```",
    "```javascript\n/* 🎈 Don’t let that answer deflate you! */\n```",
    "```jsonc\n/* 🌪 Not the eye of the storm! */\n```",
    "```kotlin\n// 🚦 Wait for the green light!\n```",
    "```lua\n-- 🛤 Took a slight detour!\n```",
    "```markdown\n* 🕵️ Let’s investigate that again! *\n```",
    "```nginx\n# 💡 A little more illumination needed!\n```",
    # ... And more
]
    

    async def stop_timer(self, user_id: int):
        """Stops the ongoing timer for the given user and deletes the associated timer message."""
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

        # Cancel the timer task if it exists
        timer_task = timer_data.get("task")
        if timer_task:
            timer_task.cancel()
            logging.info(f'Stopped timer for user_id {user_id}')

        # Delete the timer message
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
        user_id = user.id  # Get the user_id from the discord.User object
        try:
            user = await bot.fetch_user(user_id)  # fetch_user expects a snowflake ID
        except discord.errors.HTTPException as e:
            logging.error(f"Failed to fetch user: {e}")
            return
 
        difficulty = self.user_difficulty.get(user_id, 'easy')
        global quiz_completion_counter
        if user_id not in self.user_scores or user_id not in self.current_question:
            
            return
        else:
            quiz_completion_counter += 1


        # Deleting the last question message, if exists
        last_question_msg_id = self.current_question_message.get(user_id)
        if last_question_msg_id:
            try:
                await dm_channel.delete_message(last_question_msg_id)  # Directly deleting the message using its ID
            except discord.errors.NotFound:
                logging.warning(f"Last question message for user_id {user_id} already deleted or not found.")
            except Exception as e:
                logging.error(f"Error deleting last question message for user_id {user_id}: {e}")

        # Calculating quiz metrics
        answered_questions_count = self.questions_answered.get(user_id, 0)
        average_time = (self.total_time_taken[user_id] / answered_questions_count) if answered_questions_count > 0 else 0
        efficiency_ratio = self.user_scores[user_id] / len(quiz_data.get(difficulty, []))

        # Building and sending the quiz results embed
        embed = discord.Embed(title="🎉 Quiz Results", color=discord.Color.blue())
        embed.description = f"**{user.mention}, here's how you did!**"
        embed.add_field(name="📊 Efficiency", value=f"{efficiency_ratio:.2f}", inline=True)
        embed.add_field(name="📝 Answered", value=f"{answered_questions_count}", inline=True)
        embed.add_field(name="🎯 Correct", value=f"{self.user_scores[user_id]}", inline=True)
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
            embed.add_field(name="🏆 Leaderboard", value=leaderboard_message, inline=False)
            embed.add_field(name="User Participation", value=user_participation_str, inline=False)

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

            # Calculate overall quiz completion rate
            overall_completion_rate = sum(user_completion_rates.values()) / len(user_completion_rates) if user_completion_rates else 0

            return overall_completion_rate, user_participation_str
        except Exception as e:  # General exception handler
            logging.error(f"Error occurred in calculate_metrics: {e}\n{traceback.format_exc()}")

    
        
    async def update_time_taken(self, user_id: int):
        logging.debug(f"Entering update_time_taken for user_id {user_id}")

        # Calculate the time taken for the current question
        end_time = time.time()
        time_taken = end_time - self.question_start_time[user_id]

        # Update the total time taken and the number of questions answered
        self.update_questions_answered(user_id)  # Call the new method here

        self.total_time_taken[user_id] = self.total_time_taken.get(user_id, 0) + time_taken
        self.question_start_time[user_id] = end_time  # Reset the start time for the next question

        logging.debug(f"Exiting update_time_taken for user_id {user_id}")
    async def handle_user_scores(self, user_id: int, reset_streak: bool = False):

        """Handle user scores and optional streak reset."""
        self.user_scores[user_id] = self.user_scores.get(user_id, 0) + 1
        if reset_streak:
            self.user_streaks[user_id] = 0
        else:
            self.user_streaks[user_id] = self.user_streaks.get(user_id, 0) + 1


    async def trigger_animation(self, channel: discord.TextChannel, is_correct: bool):
        self.message_bank = self.CORRECT_RESPONSES if is_correct else self.wrong_answer_responses
        self.chosen_message = random.choice(self.message_bank)
        initial_color = discord.Color.green() if is_correct else discord.Color.red()
        self.message = await channel.send(embed=discord.Embed(description="_ _", color=initial_color))  # Initial empty message



    def prepare_feedback(self, is_correct: bool, correct_answer: str = None, hint: str = None):
        """Prepare feedback message based on the answer's correctness."""
        if is_correct:
            return random.choice(self.CORRECT_RESPONSES)  # Assuming CORRECT_RESPONSES is a list
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
        question_data = quiz_data.get(difficulty, [])[q_index]
    
        # Handling the case where question_data is None or out of range
        if question_data is None:
            logging.error(f"No questions available for difficulty {difficulty} at index {q_index}")
            return
    
        shuffled_options = random.sample(question_data["options"], len(question_data["options"]))

        color_scheme = {
            'easy': discord.Color.from_rgb(102, 255, 102),
            'medium': discord.Color.from_rgb(255, 255, 102),
            'hard': discord.Color.from_rgb(255, 102, 102)
        }
    
        old_question_message_id = self.current_question_message.pop(user_id, None)
        if old_question_message_id:
            try:
                old_message = await dm_channel.fetch_message(old_question_message_id)
                await old_message.edit(content='Please ignore this message.')  # Edit the old message
            except discord.NotFound:
               logging.warning(f"Old message {old_question_message_id} not found")
    
        # Prepare the question embed
        embed = discord.Embed(
            title=f"Question {q_index + 1}",
            description=question_data["question"],
            color=color_scheme[difficulty],
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Question {q_index + 1}/{len(quiz_data[difficulty])} | Difficulty: {difficulty.capitalize()}")

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
        await start_timer(user, user_id, loading_message, q_index)  # Updated argument

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
        await self.handle_user_scores(user_id, reset_streak=True)
        try:
            await self.send_feedback(user, correct_answer, hint)
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


    async def send_error_embed(self, ctx, error):
        """Send an error message embed to the invoking user."""
        user = ctx.author
        try:
            dm_channel = await get_dm_channel_for_user(user)
            logging.info(
                f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}"
            )

            embed = discord.Embed(
                title="Error",
                description=str(error),
                color=discord.Color.red(),
            )
            await dm_channel.send(embed=embed)
            return
        except Exception as e:
            logging.error(
                f"Failed to send error embed to user {user.id}: {e}",
                exc_info=True,
            )



    async def proceed_to_next_question(self, user, user_id, q_index):
        user_id = user.id  # Assuming 'user' is a Discord User object
        user = await bot.fetch_user(user_id)
        dm_channel = await get_dm_channel_for_user(user)
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")
 
        logging.info(f'Proceeding to next question: user_id={user_id}, q_index={q_index}')

        # Ensure difficulty is set correctly
        difficulty = self.user_difficulty.get(user_id)
        questions_list = quiz_data.get(difficulty, [])

        if not questions_list:
            logging.error(f'No questions available for difficulty {difficulty}')
            return

        # Stop any ongoing timer for the user
        await self.stop_timer(user_id)

        # Increment the question index
        next_q_index = q_index + 1

        # Check if there are more questions available
        if next_q_index >= len(questions_list):
            logging.info(f'No more questions for user_id={user_id}. Ending quiz.')
            await self.end_quiz(user)
            return

        # Send the next question
        await asyncio.sleep(0.3)  # A short delay
        await self.send_question(dm_channel, user_id, next_q_index)  # Added self

    
        logging.info(f'Successfully proceeded to next question or ended quiz for user_id={user_id}')

    # Updated send_feedback method to accept three arguments
    async def send_feedback(self, user: discord.User, question: str, correct_answer: str, hint=None):
        """Sends feedback to the user after answering a question."""

        # Send the condensed question
        await user.send(f"Question: {question}")

        # Create the feedback embed
        embed = discord.Embed(title="Feedback", description="Let's review.", color=discord.Color.blue())
        embed.add_field(name="Correct Answer", value=correct_answer)
        if hint:
            embed.add_field(name="Hint", value=hint)
        embed.set_footer(text=f"Keep going, {user.name}!")

        # Send the feedback embed and add the reactions
        feedback_msg = await user.send(embed=embed)
        await feedback_msg.add_reaction("🤖")  # AI Chat button
        await feedback_msg.add_reaction("⏸️")  # Pause button

        # Wait for the user's reaction
        await self.wait_for_reaction(user, feedback_msg, question, correct_answer)  # Pass both question and correct_answer


    async def wait_for_reaction(self, user: discord.User, feedback_msg, question: str, correct_answer: str):
        """Waits for the user's reaction to take appropriate action."""

        def check_reaction(reaction, user_reacting):
            return str(reaction.emoji) in ["🤖", "⏸️", "▶️"] and user_reacting == user and reaction.message.id == feedback_msg.id

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=120, check=check_reaction)
            if str(reaction.emoji) == "🤖":
                await self.start_ai_conversation(user, question, correct_answer)

            elif str(reaction.emoji) == "⏸️":
                # Pause the quiz
                await user.send("Quiz paused. Click ▶️ to resume.")
            elif str(reaction.emoji) == "▶️":
                # Resume the quiz
                await self.proceed_to_next_question(user)

        except asyncio.TimeoutError:
            pass  # Handle the timeout if needed


    async def call_gpt3(self, prompt, conversation_token=None):
        """
        Calls the OpenAI GPT-3 engine with the provided prompt and optional conversation context.

        Args:
            prompt (str): The prompt to send to GPT-3.
            conversation_token (str, optional): A token representing the ongoing conversation context.

        Returns:
            dict: The response from GPT-3.
        """
        try:
            # Ensure the API key is set
            if not OpenAI.api_key:
                OpenAI.api_key = os.getenv("OPENAI_API_KEY")

                if not OpenAI.api_key:
                    raise ValueError("Error: Missing OPENAI_API_KEY environment variable")

            # Construct the request data
            data = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]}
            
            if conversation_token:
                data["conversation_token"] = conversation_token

            response = OpenAI.ChatCompletion.create(**data)

            return response

        except OpenAI.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {e}")
            return {"choices": [{"text": "Sorry, I encountered an error while processing your request. Please try again."}]}

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return {"choices": [{"text": "Sorry, an unexpected error occurred. Please try again."}]}

    async def start_ai_conversation(self, user, question, correct_answer):
        """
        Start a conversation between the AI and the user.

        Args:
            user: The Discord user instance.
            question (str): The question that the user struggled with.
            correct_answer (str): The correct answer to the question.
        """
        try:
            # Construct the initial prompt for clarity
            initial_prompt = f"I had trouble understanding why the correct answer to '{question}' is '{correct_answer}'. Can you explain it to me?"
            response = await self.call_gpt3(initial_prompt)

            ai_msg = await user.send(response["choices"][0]["text"])
            guidance_msg = await user.send("You're now chatting with the AI. Type your questions or thoughts. Click ▶️ when you're ready to continue the quiz.")
            self.start_chat_with_ai(user.id)

            ai_conversation_history = [ai_msg, guidance_msg]
            conversation_token = None  # If your response contains a conversation token, initialize and update it here

            while self.is_chatting_with_ai(user.id):
                def check(m):
                    return m.author == user and not m.content.startswith("▶️")

                user_msg = await self.bot.wait_for('message', check=check)

                if 'conversation_token' in response:  # If your model supports conversation tokens
                    conversation_token = response['conversation_token']

                response = await self.call_gpt3(user_msg.content, conversation_token)
                ai_reply = await user.send(response["choices"][0]["text"])
                ai_conversation_history.append(ai_reply)

            # Add the resume reaction
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

    


    async def wait_for_ai_reaction(self, user: discord.User, feedback_msg, correct_answer: str):
        """
        Waits for the user's reaction to the feedback message and initiates an AI conversation if the AI reaction is used.
        
        Args:
            user (discord.User): The user who is expected to react.
            feedback_msg (discord.Message): The feedback message the user is reacting to.
            correct_answer (str): The correct answer to the question that was asked.
        """

        def check_reaction(reaction, user_reacting):
            """Checks if the reaction is relevant."""
            # Ensure the reaction is to the correct message, by the correct user, and is the correct emoji
            return (
                user_reacting == user
                and reaction.message.id == feedback_msg.id
                and str(reaction.emoji) == "🤖"  # Here we only proceed if the reaction is the bot emoji
            )

        try:
            # Wait for a reaction to be added. Timeout after 60 seconds.
            await self.bot.wait_for('reaction_add', timeout=60.0, check=check_reaction)

            # If the correct reaction is given, start the AI conversation.
            await self.start_ai_conversation(user, correct_answer)

        except asyncio.TimeoutError:
            # If 60 seconds pass without the correct reaction, you could send a follow-up message, log, etc.
            logging.info(f"No reaction from {user.name} after the feedback. Proceeding without AI conversation.")
            # Optional: Send a message, handle the lack of reaction, or transition to the next state as appropriate.

        except Exception as e:
            # For any other unexpected exception, log the error for debugging.
            logging.error(f"An error occurred while waiting for reaction: {e}", exc_info=True)
            # Optional: Send a user-friendly message to the user or take necessary recovery steps.



    async def word_animation(self, user, words, delay=0.75):
        if not words:
            logging.warning('word_animation called with empty words list.')
            return

        for word in words:
            try:
                message = await user.send(word)
                await asyncio.sleep(delay)
                await message.delete()
            except Exception as e:
                logging.error('Error in word_animation: %s', e, exc_info=True)
                await user.send("Oops! Something went wrong during the animation. Please try again later.")

    async def reaction_animation(self, user, reactions, initial_message="Great Job!", delay=0.5):
        if not reactions:
            logging.warning('reaction_animation called with empty reactions list.')
            return

        try:
            delay = max(0.1, float(delay))  # Ensure delay is non-negative and at least 0.1 seconds
            message = await user.send(initial_message)
            for reaction in reactions:
                await message.add_reaction(reaction)
                await asyncio.sleep(delay)
            await asyncio.sleep(2)
            await message.delete()
        except Exception as e:
            logging.error('Error in reaction_animation: %s', e, exc_info=True)
            await user.send("Oops! Something went wrong during the animation. Please try again later.")

    async def color_animation(self, user, colors, delay=1):
        if not colors:
            logging.warning('color_animation called with empty colors list.')
            return

        try:
            delay = max(0.1, float(delay))  # Ensure delay is non-negative and at least 0.1 seconds
            message = await user.send(embed=discord.Embed(title="Correct!", color=colors[0]))
            for color in colors[1:]:
                await asyncio.sleep(delay)
                await message.edit(embed=discord.Embed(title="Correct!", color=color))
            await asyncio.sleep(2)
            await message.delete()
        except Exception as e:
            logging.error('Error in color_animation: %s', e, exc_info=True)
            await user.send("Oops! Something went wrong during the animation. Please try again later.")








    

    async def update_progress_bar(self, user: discord.User, ctx, q_index):
        """Update the progress bar for the specified user and question index."""
        user = ctx.author
        user_id = user.id
        dm_channel = await get_dm_channel_for_user(user)
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")


        difficulty = self.user_difficulty.get(user_id)
        if difficulty not in quiz_data:
            logging.error(f"Difficulty {difficulty} not found in questions dictionary.")
            return

        if user_id not in self.current_question:
            logging.error(f"No questions found for user_id {user_id}")
            return

        total_questions = len(quiz_data.get(difficulty, []))

        if not (0 <= q_index < total_questions):
            logging.error(f"Invalid q_index {q_index} for user_id {user_id}")
            return

        progress = int((q_index / total_questions) * 100)
        progress_embed = self.progress_bar(progress)  # Using the progress_bar method

        # Check for an existing progress message and delete it
        progress_message_data = self.progress_messages.get(user_id)
        if progress_message_data:
            if isinstance(progress_message_data, discord.Message):
                await progress_message_data.delete()
                self.progress_messages.pop(user_id, None)  # Remove the old message reference

        # Send a new progress message and store its message object
        new_message = await dm_channel.send(embed=progress_embed)
        self.progress_messages[user_id] = new_message
        print(f'q_index: {q_index}, Total Questions: {len(self.current_question[user_id])}')



    async def update_timer_position(self, user, user_id, new_question_message):
        # Delete the old timer message
        old_timer_data = self.ongoing_timers.get(user_id)
        if old_timer_data:
            old_timer_message_id = old_timer_data.get("message_id")
            if old_timer_message_id:
                try:
                    old_message = await user.fetch_message(old_timer_message_id)
                    await old_message.delete()
                except discord.errors.NotFound:
                    logging.warning(f"Old timer message for user_id {user_id} already deleted.")

       
    # Function to set user difficulty
    def set_user_difficulty(self, user_id, difficulty):
        self.user_difficulty[user_id] = difficulty


