const { sendPost } = require('../feishu-common/index.js');

async function main() {
    const args = require('minimist')(process.argv.slice(2));
    
    // Usage: node skills/feishu-post/index.js --title "Title" --text "Line1\nLine2" --target "open_id"
    // Rich Text Format: 
    // Supports markdown-like input in 'text' argument? 
    // Or simple line breaks.
    // For now, let's keep it simple: Text -> Paragraphs
    
    const title = args.title || 'Notification';
    const text = args.text || '';
    const target = args.target;

    if (!target) {
        console.error('Error: --target is required');
        process.exit(1);
    }

    // Convert newlines to multiple paragraph elements
    const lines = text.split('\\n');
    const content = [
        lines.map(line => ({
            tag: 'text',
            text: line
        }))
    ];

    const postContent = {
        zh_cn: {
            title: title,
            content: content
        }
    };

    try {
        const result = await sendPost(target, postContent);
        console.log(JSON.stringify(result, null, 2));
    } catch (error) {
        console.error('Failed to send post:', error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}
