function loadFeishuClient() {
  try {
    return require("../../feishu-common/index.js");
  } catch (err) {
    const depErr = new Error(
      "Missing dependency: feishu-common. Install feishu-common skill first, then retry.",
    );
    depErr.cause = err;
    throw depErr;
  }
}

module.exports = loadFeishuClient();
