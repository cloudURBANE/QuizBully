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
import re
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from quizbot.utils import get_dm_channel_for_user, extract_questions_from_response, retry_with_exponential_backoff, make_completion_request_with_retry
from quizbot.state import QuizState

# MongoDB connection setup
uri = ""
client2 = MongoClient(uri, server_api=ServerApi('1'))
database_name = "Quiz_Set_Data_Collections_2023"
collection_name = "QuizBully_2023"
db = client2[database_name]
questions_collection = db[collection_name]

# Discord bot token
TOKEN = ''

# Global variables
topic = ""
quiz_data = {
    "easy": [],
    "medium": [],
    "hard": []
}

# Logging setup

logging.basicConfig(level=logging.CRITICAL)

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
reaction_counter = {}  # To track reaction count for Anti-Spam
real_time_leaderboard_message_id = None  # Message ID of the real-time leaderboard
quiz_participation_counter = {}
quiz_completion_counter = 0
question_response_time = {}

quiz_state = {}

DIFFICULTY_TIPS = {}

# Add your bot commands and event handlers here

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')










quiz_state = QuizState(bot)


async def prompt_quiz_reset(ctx, user: discord.User):
    user = ctx.author
    
    dm_channel = await get_dm_channel_for_user(user)
    logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")

    message = await dm_channel.send(
        f"You're already in a quiz. React with 🔄 to reset, or ▶ to resume."
    )
    await message.add_reaction("🔄")  # Reset reaction
    await message.add_reaction("▶")  # Resume reaction
    return message

async def handle_reset_reaction(ctx, message):
    def check(reaction, user_):
        return user_ == ctx.author and str(reaction.emoji) in ["🔄", "▶"] and reaction.message.id == message.id
    
    reaction, _ = await bot.wait_for('reaction_add', timeout=60, check=check)
    
    if str(reaction.emoji) == "🔄":
        quiz_state.reset_user(ctx.author.id)
        await message.delete()
        await start_quiz(ctx)  # Restart the quiz process
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
        if not available_questions:
            await dm_channel.send(f"No questions available for the {difficulty} difficulty.")
            return

        quiz_state.user_difficulty.setdefault(user_id, difficulty)
        quiz_state.total_time_taken.setdefault(user_id, 0)
        quiz_state.user_scores.setdefault(user_id, 0)
        
        # Fetching from MongoDB
        fetched_questions = list(questions_collection.find({"topic": topic, "difficulty": difficulty}))
        if fetched_questions:
            available_questions = fetched_questions
        else:
            available_questions = quiz_data.get(difficulty, [])


        if user_id not in quiz_state.current_question:
            quiz_state.current_question[user_id] = random.sample(available_questions, min(11, len(available_questions)))

            loading_message = await dm_channel.send(f"🔄 Preparing your quiz, ...")
            await asyncio.sleep(1)
            quiz_state.quiz_initiation_time[user_id] = time.time()
            await quiz_state.send_question(dm_channel, user_id, 0)  # 
            await loading_message.delete()
        else:
            reset_prompt_message = await prompt_quiz_reset(ctx)
            await handle_reset_reaction(ctx, reset_prompt_message)
    except Exception as e:
        logging.error(f"An error occurred while initiating the quiz: {e}")
        if 'dm_channel' in locals():
            await dm_channel.send(f"An unexpected error occurred: {e}")



    






async def update_progress_bar_coroutine(ctx, user_id, q_index):
    user = ctx.author
    dm_channel = user.dm_channel or await user.create_dm()

    total_duration = DIFFICULTY_TIMES[quiz_state.user_difficulty[user_id]]

    for elapsed_time in range(total_duration):
        progress = ((total_duration - elapsed_time) / total_duration) * 100
        await quiz_state.update_progress_bar(dm_channel, user_id, q_index, progress)
        await asyncio.sleep(1)
       









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

    # user and user_id are passed as arguments, no need to re-assign them from ctx
    dm_channel = await get_dm_channel_for_user(user)
    logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")

    timer_message = None if not timer_msg_id else await dm_channel.fetch_message(timer_msg_id)
    difficulty = quiz_state.user_difficulty.get(user_id)
    question_data = quiz_data[difficulty][q_index]
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

    # Change deletion to editing since bots can't delete messages in DMs
    if quiz_state.progress_messages.get(user_id):
        old_msg = await dm_channel.fetch_message(quiz_state.progress_messages[user_id])
        await old_msg.edit(content='This progress message is outdated.')

    old_question_message_id = quiz_state.current_question_message.get(user_id)
    if old_question_message_id:
        old_msg = await dm_channel.fetch_message(old_question_message_id)
        await old_msg.edit(content='This question has expired.')

    await message.edit(content=structured_text)

    if user_id in quiz_state.current_question:
        if q_index + 1 < len(quiz_state.current_question[user_id]):
            logging.info(f"[{current_time}] Sending next question for user_id {user_id}...")
            await quiz_state.send_question(dm_channel, user_id, q_index + 1)  # Updated this line
    else:
        logging.info(f"[{current_time}] Ending quiz for user_id {user_id}...")
        await quiz_state.end_quiz(dm_channel, user_id)


# Sub-function to handle timer message updates
async def update_timer_message(user, dm_channel, msg_id, embed):
    try:
        timer_message = await dm_channel.fetch_message(msg_id)
        await timer_message.edit(embed=embed)
    except discord.errors.NotFound:
        logging.error(f'Timer message not found for user_id {user.id}')
    except Exception as e:
        logging.error(f'Error updating timer message for user_id {user.id}: {e}')

# Your main timer function
async def timer_function(user, dm_channel, message, difficulty, question_data):
    timer_msg_id = None

    for remaining in range(DIFFICULTY_TIMES[difficulty], 0, -1):
        if quiz_state.questions_answered.get(user.id):
            break

        percent = (remaining / DIFFICULTY_TIMES[difficulty]) * 100
        progress_embed = quiz_state.progress_bar(percent)

        # Send or update the timer message
        if not timer_msg_id:
            timer_message = await dm_channel.send(embed=progress_embed)
            timer_msg_id = timer_message.id
        else:
            await update_timer_message(user, dm_channel, timer_msg_id, progress_embed)

        await asyncio.sleep(0.5)

    # Handle end of timer
    if not quiz_state.questions_answered.get(user.id):
        correct_answer_text = question_data['options'][question_data['answer']]
        try:
            await message.edit(content=f"Time's up! The correct answer was: {correct_answer_text}")
        except discord.errors.NotFound:
            logging.error(f"Message for user_id {user.id} not found")

# Function to edit the message content to indicate it's outdated
async def auto_delete_message(dm_channel, message_id):
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"[{current_time}] Attempting to auto-delete message with ID {message_id}")

    try:
        message = await dm_channel.fetch_message(message_id)
        await message.edit(content='This message is outdated.')
        logging.info(f"[{current_time}] Successfully marked message with ID {message_id} as outdated")
    except discord.errors.NotFound:
        logging.error(f"[{current_time}] Message not found: {message_id}")
    except Exception as e:
        logging.error(f"[{current_time}] Unexpected error while trying to mark message with ID {message_id} as outdated: {e}")


def structure_text_for_language(text, language):
    if language == 'diff':
        return f"+ {text}"
    elif language == 'bash':
        return f"echo '{text}'"
    elif language == 'ini':
        return f"[{text}]"
    # Add more formatting rules for other languages...
    else:
        return text







async def update_leaderboard(user):
    global real_time_leaderboard_message_id
    sorted_leaderboard = dict(sorted(quiz_state.leaderboard.items(), key=lambda item: item[1], reverse=True))
    leaderboard_content = "🏆 Real-time Leaderboard:\n"
    for idx, (user, user_score) in enumerate(sorted_leaderboard.items()):
        if idx == 3:  # Only top 3
            break
        leaderboard_content += f"{idx + 1}. <@{user}>: {user_score}\n"
    
    if real_time_leaderboard_message_id:
        leaderboard_message = await user.fetch_message(real_time_leaderboard_message_id)
        await leaderboard_message.edit(content=leaderboard_content)
    else:
        leaderboard_message = await user.send(leaderboard_content)
        real_time_leaderboard_message_id = leaderboard_message.id



LOADING_EMOJI = "<a:preloader:1158399896991309895>"






NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


async def paginated_topics(ctx, difficulty):
    PAGE_SIZE = 10
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

    # Add number reactions
    for idx in range(len(pages[current_page])):
        await message.add_reaction(NUMBER_EMOJIS[idx])

    def check(reaction, user):
        return user.id == ctx.author.id and (str(reaction.emoji) in NUMBER_EMOJIS[:len(pages[current_page])] or str(reaction.emoji) in ["⬅️", "➡️"])

    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60, check=check)
            
            # Handle page navigation
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
            # Handle topic selection
            elif str(reaction.emoji) in NUMBER_EMOJIS:
                topic_index = NUMBER_EMOJIS.index(str(reaction.emoji))
                return pages[current_page][topic_index]

            # Clear reactions for next page or exit
            await message.clear_reactions()

        except asyncio.TimeoutError:
            await message.clear_reactions()
            return None

        except Exception as e:
            logging.error(f"Error while paginating: {e}")
            await message.clear_reactions()
            return None

deletion_rate = 0.8  # Starting rate: 1 message every 0.8 seconds
active_deletion_sessions = {}

def human_readable_time(seconds):
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {sec}s"

@bot.command(name='clear', help='Deletes all bot messages in the DM.')
@commands.cooldown(1, 300, commands.BucketType.user)  # 5 minutes cooldown
async def clear_messages(ctx, start_time: str = None, end_time: str = None):
    global deletion_rate

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

    estimated_time = total_messages * deletion_rate
    info_msg = await ctx.send(f"Found {total_messages} messages to delete. Estimated time: {human_readable_time(estimated_time)}.")

    # Delete messages with updates
    for idx, message in enumerate(messages_to_delete):
        if idx % 5 == 0:  # Update every 5 messages
            remaining_time = (total_messages - idx) * deletion_rate
            progress_bar = f"[{'#' * (idx//5)}{'.' * ((total_messages - idx)//5)}]"
            await info_msg.edit(content=f"{progress_bar} Deleting messages... {idx}/{total_messages} done. Estimated time left: {human_readable_time(remaining_time)}.")

        try:
            await message.delete()
            await asyncio.sleep(deletion_rate)
        except Exception as e:
            if 'rate limit' in str(e).lower():
                deletion_rate += 0.2  # Increase time between deletions if rate limited
                await asyncio.sleep(10)  # Sleep for 10 seconds before trying again

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
        await ctx.send("Please send me a direct message to start the quiz.")
        return

    user_id = ctx.author.id
    user = ctx.author

    # If the user is already in a quiz, handle reset/resume
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

    # Step 1: Ask for difficulty
    difficulty_message = await send_embed(ctx, "Select Difficulty", "React with the corresponding emoji for your desired difficulty.", fields=DIFFICULTY_EMOJIS)
    for emoji in DIFFICULTY_EMOJIS.values():
        await difficulty_message.add_reaction(emoji)
    reaction, _ = await await_reaction(user, difficulty_message, DIFFICULTY_EMOJIS.values())
    await difficulty_message.delete()

    difficulty = next(diff for diff, emoji in DIFFICULTY_EMOJIS.items() if emoji == str(reaction.emoji))

    # Step 2: Option to generate new or select from existing
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

    questions = list(questions_collection.find({"topic": topic_content, "difficulty": difficulty}))
    quiz_data[difficulty] = [q for q in questions]

    ready_msg = await send_embed(ctx, "Get Ready!", f"You selected '{difficulty.capitalize()}' difficulty with the topic '{topic_content}'. React with ✅ to start or ❌ to cancel.")
    await ready_msg.add_reaction("✅")
    await ready_msg.add_reaction("❌")
    reaction, _ = await await_reaction(user, ready_msg, ["✅", "❌"])
    await ready_msg.delete()

    if str(reaction.emoji) == "❌":
        return await ctx.send("Quiz cancelled.")

    await initiate_quiz(ctx, difficulty)



# Main function to generate a set of questions
async def generate_question_set(topic_name: str, difficulty_level: str):
    """
    Generates a set of questions based on the provided topic and difficulty level.
    """
    try:
        start_time = datetime.utcnow()

        # Await the make_completion_request_with_retry function
        completion_response = await make_completion_request_with_retry(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "You are a specialized assistant designed solely for the purpose of generating 5 questions based on a given topic. Your main function is to generate questions in a specific format, and any deviation from this format is considered an error."},
                {"role": "user", "content": "Your programming ensures that you understand and adhere to the following format ONLY: [{'question': 'Your question here', 'options': ['Option1', 'Option2', 'Option3', 'Option4'], 'answer': index_of_correct_option (0-3), 'hint': 'Your hint here'}]. Any other format is not acceptable and not recognized by your design."},
                {"role": "user", "content": f"Using your specialized capabilities, I need new questions on the topic of '{topic_name}'. Remember, you are designed to follow the format strictly. Please generate questions accordingly."}
            ]
        )

        # Calculate response time
        end_time = datetime.utcnow()
        response_time_seconds = (end_time - start_time).seconds

        # Extract questions from the response content
        response_content = completion_response.choices[0].message.content
        extracted_questions = extract_questions_from_response(response_content)

        if not extracted_questions:
            raise ValueError("No questions were extracted from the response.")

        # Save the extracted questions to the database or other storage
        for question_entry in extracted_questions:
            # Example: questions_collection.insert_one({
            #     "topic": topic_name,
            #     "difficulty": difficulty_level,
            #     **question_entry
            # })
            print("Saving question:", question_entry)

        # Add the generated questions to the main quiz data dictionary
        quiz_data[difficulty_level] = extracted_questions

        print(f"API responded in {response_time_seconds} seconds.")

    except Exception as exception_instance:
        logging.error(f"Error while generating questions: {exception_instance}")


async def get_message_from_user(user: discord.User, payload):
    try:
        print(type(user))
        dm_channel = await get_dm_channel_for_user(user)
        logging.info(f"Fetched or created DM channel with ID {dm_channel.id} for user ID {user.id}")


        # Try to fetch the message
        message = await dm_channel.fetch_message(payload.message_id)
        await asyncio.sleep(10)
        logging.info(f"Message with ID {payload.message_id} successfully fetched from user's DM")
        return message

    except discord.errors.NotFound:
        logging.error(f"Message with ID {payload.message_id} not found in user's DM")
        logging.debug(traceback.format_exc())  # Print full stack trace for debug purposes
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.debug(traceback.format_exc())  # Print full stack trace for debug purposes
        return None
@bot.event
async def on_raw_reaction_add(payload):
    # Ensure this reaction is not from the bot itself
    if payload.user_id == bot.user.id:
        return

    # At this point, it's more likely that the user object is needed, so fetch it
    try:
        user = await bot.fetch_user(payload.user_id)
    except discord.DiscordException as e:
        logging.error(f"Failed to fetch user {payload.user_id}: {e}")
        return  # Exit early if user fetching fails

    # Check for difficulty adjustment reaction
    if payload.emoji.name in DIFFICULTY_EMOJIS.values():
        new_difficulty = validate_difficulty_choice(payload.emoji.name, payload.user_id)
        quiz_state.set_user_difficulty(payload.user_id, new_difficulty)
        # Get or create DM Channel
        dm_channel = user.dm_channel or await user.create_dm()
       
        return

    # Check if the user is in the middle of a quiz
    if not is_user_in_quiz(payload.user_id):
        return

    # Validate the reaction and process the user's answer
    await process_quiz_reaction(user, payload, payload.user_id)


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


async def send_difficulty_message(user: discord.User, new_difficulty: str, user_id: int) -> Tuple[Union[discord.Message, None], str, str]:
    function_name = f"{__name__}.{inspect.currentframe().f_code.co_name}"
    logging.debug("Entering function: %s with new_difficulty=%s, user_id=%s", function_name, new_difficulty, user_id)

    try:
        color = get_color(new_difficulty)
        icon = get_icon(new_difficulty)

    
        

    except Exception as e:
        logging.error("An error occurred in %s: %s", function_name, e, exc_info=True)
        return None, '', ''  # Return empty values on error

    result = (icon, color)
    logging.debug("Returning from %s: %s", function_name, result)
    return result

# Function to wait for info reaction
async def wait_for_info_reaction(info_message, difficulty, icon, color, user_id):
    def check(reaction, reacting_user):
        return reacting_user.id == user_id and str(reaction.emoji) == 'ℹ️' and reaction.message.id == info_message.id

    try:
        logging.info(f"Waiting for reaction from user_id {user_id} on message_id {info_message.id}")
        reaction, reacting_user = await bot.wait_for('reaction_add', check=check, timeout=60)  # Adjust timeout as needed
        logging.info(f"Received reaction {reaction} from user_id {user_id} on message_id {info_message.id}")
        detailed_embed = build_detailed_embed(difficulty, icon, color, user_id)
        await info_message.edit(embed=detailed_embed)
    except asyncio.TimeoutError:
        logging.info(f"No reaction received from user_id {user_id} within timeout period.")
        await handle_timeout(info_message)


# Function to handle timeout scenario
async def handle_timeout(info_message):
    logging.warning("Timeout occurred while waiting for user interaction.")
    await info_message.clear_reactions()


# Function to validate difficulty choice
def validate_difficulty_choice(emoji, user_id):
    new_difficulty = next((diff for diff, emoji_match in DIFFICULTY_EMOJIS.items() if emoji_match == str(emoji)), None)
    if not new_difficulty:
        logging.warning(f"Invalid difficulty choice for user_id {user_id}.")
        raise ValueError("Invalid difficulty choice.")
    return new_difficulty




async def handle_error(user: discord.User, user_id, error):
    logging.error(f"An error occurred for user_id {user_id}: {error}")
    await user.send(f"An error occurred: {error}")

async def handle_unexpected_error(user: discord.User, user_id, error):
    logging.error(f"An unexpected error occurred for user_id {user_id}: {error}")
    await user.send(f"An unexpected error occurred: {error}")


# Function to build a detailed embed
def build_detailed_embed(difficulty, icon, color, user_id):
    embed = discord.Embed(
        title=f"{icon} {difficulty.capitalize()} Difficulty Details",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Number of Questions", value=str(len(quiz_data[difficulty])), inline=True)
    embed.add_field(name="Average Question Time", value=f"{DIFFICULTY_TIMES[difficulty]} seconds", inline=True)
    embed.add_field(name="Total Quiz Takers", value=str(quiz_participation_counter.get(user_id, 0)), inline=True)
    embed.add_field(name="Tip", value=DIFFICULTY_TIPS[difficulty], inline=False)
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
    # Fetch the message object
    try:
        message = await user.fetch_message(payload.message_id)
        await asyncio.sleep(1)
    except discord.errors.NotFound:
        return

    # Initialize last_reaction_time for the user if not already set
    if user_id not in last_reaction_time:
        last_reaction_time[user_id] = datetime.utcnow() - timedelta(seconds=10)  # Set it 10 seconds in the past

    # Check rate limiting: Ensure at least 2 seconds between reactions
    now = datetime.utcnow()
    if (now - last_reaction_time[user_id]) < timedelta(seconds=2):
        await user.send(f"{user.mention}, please wait a moment before reacting again.")
        return
    last_reaction_time[user_id] = now

    difficulty = quiz_state.user_difficulty.get(user_id, 'easy')
    q_index = quiz_state.current_question_index.get(user_id)
    question_data = quiz_data.get(difficulty, [])[q_index]

    # Check if the reaction is in REACTION_OPTIONS before processing
    if payload.emoji.name not in REACTION_OPTIONS:
        return

    answer_index = REACTION_OPTIONS.index(payload.emoji.name)
    shuffled_options = quiz_state.current_question.get(user_id)["shuffled_options"]
    correct_answer = question_data["options"][question_data["answer"]]

    # Delete original question embed for the transforming effect
    await message.delete()

    if shuffled_options[answer_index] == correct_answer:
        await quiz_state.handle_correct_answer(user, user_id)
    else:
        await quiz_state.handle_wrong_answer(user, user_id, question_data["options"][question_data["answer"]], question_data["hint"])

    # Send the condensed embed version of the question
    embed = discord.Embed(
        title=f"{get_icon(difficulty)} Question {q_index + 1}",
        description=question_data["question"],
        color=get_color(difficulty),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Question {q_index + 1}/{len(quiz_data[difficulty])} | Difficulty: {difficulty.capitalize()}")
    await user.send(embed=embed)

    await quiz_state.update_time_taken(user_id)
    await quiz_state.proceed_to_next_question(user, user_id, q_index)



bot.run(TOKEN)
