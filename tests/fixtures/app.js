// Fixture: trigger LLM call pattern detection (openai)
const { OpenAI } = require('openai');
const client = new OpenAI();

async function run() {
    const response = await client.chat.completions.create({
        model: 'gpt-4',
        messages: [{ role: 'user', content: 'Hello' }],
    });
    return response;
}
