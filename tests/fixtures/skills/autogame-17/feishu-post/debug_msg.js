const { fetchWithAuth } = require('./utils/feishu-client.js');

async function run() {
    const msgId = 'om_x100b5747191850a0b2c501a826f753e';
    console.log('Fetching msg:', msgId);
    try {
        const res = await fetchWithAuth(`https://open.feishu.cn/open-apis/im/v1/messages/${msgId}`, { method: 'GET' });
        const data = await res.json();
        console.log('Current Msg:', JSON.stringify(data, null, 2));
        
        if (data.data && data.data.items && data.data.items[0].parent_id) {
            const parentId = data.data.items[0].parent_id;
            console.log('Fetching Parent:', parentId);
            const res2 = await fetchWithAuth(`https://open.feishu.cn/open-apis/im/v1/messages/${parentId}`, { method: 'GET' });
            const data2 = await res2.json();
            console.log('Parent Msg:', JSON.stringify(data2, null, 2));
        }
    } catch(e) {
        console.error(e);
    }
}
run();
