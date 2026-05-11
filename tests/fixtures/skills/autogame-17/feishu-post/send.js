#!/usr/bin/env node
const { fetchWithAuth } = require('./utils/feishu-client.js');
const { parseMarkdownToFeishu } = require('./utils/markdown-parser.js');
const fs = require('fs');
const path = require('path');

// --- Upstream Logic Injection (Simplified) ---
// Ported from upstream src/send.ts (m1heng/clawdbot-feishu)
// Adapted for our lightweight architecture

async function sendPost(options) {
    // Normalize common mis-usage:
    // - Feishu message_id usually starts with "om_". If user passes it as --target,
    //   interpret it as --reply-to to avoid sending an invalid open_id.
    if (options && typeof options.target === 'string' && options.target.startsWith('om_') && !options.replyTo) {
        options.replyTo = options.target;
        delete options.target;
    }

    if (options.content && !options.text) {
        options.text = options.content;
    }
    if (options.markdown && !options.text) {
        options.text = options.markdown;
    }

    let contentText = options.text || '';
    if (options.textFile) {
        try {
            if (!fs.existsSync(options.textFile)) {
                throw new Error(`File not found: ${options.textFile}`);
            }
            contentText = fs.readFileSync(options.textFile, 'utf8');
        } catch (e) {
            throw new Error(`Failed to read message file: ${e.message}`);
        }
    }

    if (!contentText && !options.content) {
        throw new Error('No content provided (use --text or --text-file)');
    }

    // Validate target/replyTo requirements
    const hasReplyTo = !!options.replyTo;
    const hasTarget = typeof options.target === 'string' && options.target.length > 0;
    if (!hasReplyTo && !hasTarget) {
        throw new Error('Missing target (use --target "ou_..." or "oc_..." or provide --reply-to "om_...")');
    }

    // Determine ID Type
    let receiveIdType = 'open_id';
    if (hasTarget) {
        if (options.target.startsWith('oc_')) receiveIdType = 'chat_id';
        else if (options.target.startsWith('ou_')) receiveIdType = 'open_id';
        else if (options.target.includes('@')) receiveIdType = 'email';
        else if (options.target.startsWith('om_')) {
            // Should have been normalized earlier; keep as explicit guard.
            throw new Error('Invalid target "om_...": message_id cannot be used as receive_id. Use --reply-to "om_..."');
        } else {
            throw new Error('Invalid target id. Expected "ou_..." (open_id), "oc_..." (chat_id), or an email address.');
        }
    }

    // Build Payload (RichText)
    // Upstream Logic: Wrap markdown in Post Object
    
    // Split text by newlines to create paragraphs
    // Unescape literal \n if passed from command line
    const rawLines = contentText.replace(/\\n/g, '\n').split(/\r?\n/);
    const contentBody = rawLines.map(line => parseMarkdownToFeishu(line));

    const postContent = {
        zh_cn: {
            title: options.title || '',
            content: contentBody
        }
    };

    const messageBody = {
        receive_id: options.target,
        msg_type: 'post',
        content: JSON.stringify(postContent)
    };

    // Support Reply (New Feature from Upstream)
    let url = `https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=${receiveIdType}`;
    if (options.replyTo) {
        url = `https://open.feishu.cn/open-apis/im/v1/messages/${options.replyTo}/reply`;
        delete messageBody.receive_id; // Reply doesn't need receive_id
    }

    // console.log(`Sending Post to ${options.target}...`);
    
    try {
        const res = await fetchWithAuth(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(messageBody)
        });
        
        const text = await res.text();
        let data;
        
        try {
            data = JSON.parse(text);
        } catch (e) {
             if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}: ${text}`);
             throw new Error(`Invalid JSON response: ${text.slice(0, 200)}...`);
        }
        
        if (!res.ok) {
            // Check if it's a recoverable error (like invalid emoji)
            const isEmojiError = data.code === 230001 && data.msg && data.msg.includes("emoji_type is invalid");
            if (!isEmojiError) {
                 throw new Error(`HTTP ${res.status} ${res.statusText}: ${JSON.stringify(data)}`);
            }
            // If it is an emoji error, flow through to the fallback logic below
        }
        
        if (data.code !== 0) {
            // Hotfix: If invalid emoji detected (230001), fallback to plain text stripping emojis
            if (data.code === 230001 && data.msg && data.msg.includes("emoji_type is invalid")) {
                 console.warn("Detected invalid emoji in Feishu post. Retrying as plain text fallback...");
                 // Fallback strategy: Send as plain text message, which renders emoji codes as text [Code]
                 // This ensures the message gets through even if the specific emoji is not supported.
                 const fallbackBody = {
                     receive_id: messageBody.receive_id,
                     msg_type: 'text',
                     content: JSON.stringify({ text: contentText })
                 };
                 
                 // Reuse URL (it might be a reply URL)
                 if (options.replyTo) {
                      delete fallbackBody.receive_id;
                 }
                 
                 const res2 = await fetchWithAuth(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(fallbackBody)
                 });
                 
                 const text2 = await res2.text();
                 const data2 = JSON.parse(text2);
                 if (data2.code === 0) return data2.data;
                 // If fallback fails, throw original error (or new one)
                 throw new Error(`API Error ${data.code}: ${data.msg} (Fallback also failed: ${data2.code} ${data2.msg})`);
            }
            throw new Error(`API Error ${data.code}: ${data.msg}`);
        }
        
        // ... (rest of function)

    } catch (e) {
        console.error(`Send Failed: ${e.message}`);
        throw e;
    }
}

// CLI Wrapper
if (require.main === module) {
    const { program } = require('commander');
    program
        .option('-t, --target <id>', 'Target ID')
        .option('-x, --text <text>', 'Text content')
        .option('-c, --content <text>', 'Content (alias for --text)')
        .option('-m, --markdown <text>', 'Markdown content (alias for --text)')
        .option('-f, --text-file <path>', 'File content')
        .option('--title <text>', 'Title')
        .option('--reply-to <id>', 'Message ID to reply to')
        .parse(process.argv);
    
    const opts = program.opts();
    
    // Safety: if --text contains shell-mangled content (missing chars),
    // try to detect and warn. Also support stdin piping as fallback.
    if (opts.text && !opts.textFile) {
        // Write to temp file to avoid shell escaping issues with special chars
        const tmpPath = path.join('/tmp', `feishu_post_${Date.now()}_${Math.random().toString(36).slice(2)}.txt`);
        fs.writeFileSync(tmpPath, opts.text);
        opts.textFile = tmpPath;
        opts.text = undefined;
        // Clean up after send
        sendPost(opts).then(() => {
            try { fs.unlinkSync(tmpPath); } catch (_) {}
        }).catch((e) => {
            try { fs.unlinkSync(tmpPath); } catch (_) {}
            process.exit(1);
        });
    } else {
        sendPost(opts).catch(() => process.exit(1));
    }
}

module.exports = { sendPost };
