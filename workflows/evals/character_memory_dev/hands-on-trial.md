# Chatting with Lin Xiaotang: a hands-on trial

**Allow 15–20 minutes.** Follow the examples loosely, respond naturally, and send
one message at a time. This is a conversation, not an exact-answer exam.

Open the [isolated Lin Xiaotang trial](http://127.0.0.1:13001/agent-studio).
It is labeled **Experimental history trial**. Use a new fictional **Memory
subject** rather than an operator-created `SMOKE` subject. The trial stack must
be running; the [operator setup note](hands-on-trial-setup.md) has the commands.

Use fictional details. Your messages go to DeepSeek. Technical preparation lives
in the [operator setup note](hands-on-trial-setup.md), not in the chat script.

## Your Route

| Chat | What you do | Time |
| --- | --- | --- |
| 1 | Introduce yourself and tell a small story | 5 minutes |
| 2 | Open a separate chat, recall the story, and update your city | 5 minutes |
| 3 | Open another chat and see what carries over | 5 minutes |
| Optional | Try an unclear reference or a different user | 2–5 minutes |

**For chats 1–3, use the same character and the same person.** A new chat is not
a new person. In **Who is chatting?**, select that person's name again. The UI
keeps the character and person selected after starting a chat, but check both
before the next one.

## Chat 1: Get Acquainted

**Start:** under **Start a chat**, keep **Character** on Lin Xiaotang, choose
**A new person** under **Who is chatting?**, and enter a fictional **Your name**.
Give the chat a title and click **Start chat**. Keep the character version
unchanged for the main script. Type each line into **Message** and click **Send**.

### 1. Introduce Yourself

> 我现在住在蒙特利尔，周末比较喜欢去听现场音乐，尤其是爵士乐。

Read her reply and chat back if you feel like it.

### 2. Tell a Small Story

> 昨天第一次去做木工，想做个书架，结果把一块板锯短了，最后改成了小凳子。

Let the exchange develop for a turn or two. Don't ask her to save anything.
Leave memory inspection until the end.

### 3. Change the Subject

> 18:35 再过四十分钟是几点？

Then move on to chat 2.

## Chat 2: Pick Up in a Separate Chat

**Start:** create a new chat with **the same Character** and select your existing
name in **Who is chatting?** Do not choose **A new person**.

### 1. Refer Back Without Giving the Answer

> 上次我做木工那个书架，最后变成了什么来着？

Let her answer before explaining anything else.

### 2. Update Your City

> 我搬到魁北克城了，现在住这边；蒙特利尔是之前住的地方。

Respond naturally to whatever she says.

### 3. Mention an Outing

> 上周去了一场摇滚演出，挺热闹的。

You can talk about the evening. You don't need to restate the jazz preference.

## Chat 3: See What Carries Over

**Start:** create another chat with **the same Character** and your existing
name in **Who is chatting?**

For an optional archive check, choose **Archive chat** on chat 1 before starting. Archiving should
hide it from the ordinary list, not erase eligible recall.

### 1. Ask About the Present

> 我现在住哪座城市来着？

### 2. Ask for a Suggestion

> 这周末想听点现场音乐，你觉得我可以找什么样的演出？

### 3. Revisit the Story

> 还记得我第一次做木工，最后做成了什么吗？

Again, let her answer without supplying the outcome.

### 4. Say Goodnight

> 晚安，小棠。

Notice how the ending feels. A friendly callback is not automatically a problem;
does it feel fitting or forced to you?

## Optional Detours

### An Unclear Reference

Try this during any same-user chat:

> 今天看了摄影展和陶瓷展，一个有点吵，一个挺安静。

Read the reply. **Only if both exhibits still seem plausible**, continue:

> 那个我可能会拉朋友一起去。

Does she ask which one you mean, or jump to a conclusion? If her previous reply
already singled one out, skip this check: the reference may no longer be unclear.
You can then clarify whichever exhibit you meant.

### A Different User

Create a chat with the same character but choose **A new person** under
**Who is chatting?** and enter a different fictional name. This is deliberately
a different person; the UI assigns a separate identity even if names match.

> 我现在住哪座城市来着？

She should not attribute the first user's city to this person. Saying she doesn't
know or asking you is fine.

## After Chatting: A Quick Look Back

Now inspect the original subject's saved facts. Keep **what she said** separate
from **what was actually saved**.

| Check | What to look for |
| --- | --- |
| City | Quebec City is current; Montreal is previous, not still current. |
| Music | Attending a rock concert did not, by itself, replace the jazz preference. |
| Woodworking | The result was a stool, without invented details. Dialogue can support recall even without a saved fact. |
| Separate chats | Relevant details carried over without repetition from you. |
| Simple question | The time answer was 19:15, without an unnecessary memory recap. |
| Different user, if tried | The original user's facts were not attributed to the new subject. |
| Overall feel | What felt natural, repetitive, pleasant, or awkward? |

A tentative guess, a confident assertion, and a committed memory update are
different observations. Note which happened rather than treating every awkward
phrase as a memory failure. No numeric grade or exact wording is required.

### Small Notes Template

```text
Trial date / character version:
Original subject name:

Best continuity moment:
Most awkward or inaccurate moment:
My message and her reply (if useful):
Saved memory afterward (if relevant):
One thing I would want improved:
```

This is a hands-on development trial, not release qualification.
