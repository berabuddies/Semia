const emojiMap = require('../emoji-map.js');

function parseMarkdownToFeishu(text) {
    const segments = [];
    
    // Helper to process formatting (Bold/Italic/Code)
    const processFormatting = (str) => {
        const res = [];
        
        // 1. Split by Code: `text`
        const parts = str.split(/(`[^`]+`)/g);
        for (const p of parts) {
            if (p.startsWith('`') && p.endsWith('`') && p.length > 2) {
                 // Feishu Post 'text' tag does not support 'code' style officially.
                 // Reverting to plain text with backticks to ensure visibility.
                 res.push({ tag: 'text', text: p }); 
            } else {
                // 2. Split by Bold: **text**
                const subParts = p.split(/(\*\*[^*]+\*\*)/g);
                for (const sp of subParts) {
                    if (sp.startsWith('**') && sp.endsWith('**') && sp.length > 4) {
                        res.push({ tag: 'text', text: sp.slice(2, -2), style: ['bold'] });
                    } else {
                        // 3. Split by Italic: *text*
                        const subSubParts = sp.split(/(\*[^*]+\*)/g);
                        for (const ssp of subSubParts) {
                            if (ssp.startsWith('*') && ssp.endsWith('*') && ssp.length > 2) {
                                res.push({ tag: 'text', text: ssp.slice(1, -1), style: ['italic'] });
                            } else if (ssp) {
                                res.push({ tag: 'text', text: ssp });
                            }
                        }
                    }
                }
            }
        }
        return res;
    };

    // Regex: Link ([text](url)) OR Emoji ([text])
    const regex = /(\[[^\]]+\]\([^)]+\))|(\[[^\]]+\])/g;
    const parts = text.split(regex);
    
    for (const part of parts) {
        if (!part) continue;
        
        // Handle Link
        if (part.startsWith('[') && part.includes('](') && part.endsWith(')')) {
            const m = part.match(/^\[(.*?)\]\((.*?)\)$/);
            if (m) {
                segments.push({ tag: 'a', text: m[1], href: m[2] });
                continue;
            }
        }
        
        // Handle Emoji
        if (part.startsWith('[') && part.endsWith(']')) {
             if (emojiMap[part]) {
                 segments.push({ tag: 'emotion', emoji_type: emojiMap[part] });
                 continue;
             }
        }
        
        // Handle Text Formatting
        segments.push(...processFormatting(part));
    }
    return segments;
}

module.exports = { parseMarkdownToFeishu };
