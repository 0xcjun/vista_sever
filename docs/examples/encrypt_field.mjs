// JS / Node.js 客户端示例: 把 anthropic_api_key 加密后塞进 EnvelopeIn.
//
// 安装依赖:
//   npm install libsodium-wrappers
//
// 运行 (Node.js >= 18):
//   SEAL_PK_B64=<公钥> node docs/examples/encrypt_field.mjs "sk-ant-real-key"
//
// 浏览器/打包器 (Vite/webpack/esbuild) 也直接 import 这个模块, libsodium-wrappers
// 在浏览器和 Node 都能跑.

import { realpathSync } from "node:fs";
import { pathToFileURL } from "node:url";
import sodium from "libsodium-wrappers";

const PREFIX = "enc:v1:";

/**
 * 把明文用 sealed_box 加密, 返回 `enc:v1:<kid>:<b64>` 字符串.
 *
 * 可放到任何 SecretStr 字段里, FC 入口反序列化后自动解密.
 *
 * @param {string} plaintext        明文 (如 "sk-ant-...")
 * @param {string} publicKeyB64     32 字节 X25519 公钥的 base64
 * @param {string} [kid="v1"]       key id, 与 FC 侧 VISTA_FC_SEAL_SK_<KID> 对齐
 * @returns {Promise<string>}       enc:v1:<kid>:<base64>
 */
export async function encryptField(plaintext, publicKeyB64, kid = "v1") {
  await sodium.ready;
  const pk = sodium.from_base64(publicKeyB64, sodium.base64_variants.ORIGINAL);
  if (pk.length !== 32) {
    throw new Error(`public_key 必须解码成 32 字节, got ${pk.length}`);
  }
  const message = sodium.from_string(plaintext);
  const ct = sodium.crypto_box_seal(message, pk);
  const ctB64 = sodium.to_base64(ct, sodium.base64_variants.ORIGINAL);
  return `${PREFIX}${kid}:${ctB64}`;
}

/**
 * 演示: 构造一份 factor-builder 的 EnvelopeIn, api_key 字段加密.
 */
export async function buildEnvelope(apiKeyPlain, publicKeyB64) {
  return {
    tenant: {
      user_hash: "u_demo",
      workspace_id: "EXP_DEMO",
      workspace_kind: "research",
      run_id: "demo-001",
      requested_at: "2026-05-02T00:00:00Z",
    },
    payload: {
      routes_toml_uri: "oss://vista-fc-prod/.../factor_routes.toml",
      builder_type: "claude",
      factor_numbers: 4,
      batch_size: 4,
      max_workers: 1,
      anthropic_api_key: await encryptField(apiKeyPlain, publicKeyB64),
      anthropic_base_url: "https://api.anthropic.com",
      anthropic_model: "claude-sonnet-4-6",
    },
  };
}

// ── CLI 入口 ───────────────────────────────────────────────────────────────
// 注: macOS 下 /tmp 是 /private/tmp 的符号链接, import.meta.url 走 realpath,
// 直接拼 file://${argv[1]} 在某些路径会对不上, 用 realpathSync 归一化.
const _entry = pathToFileURL(realpathSync(process.argv[1] ?? "")).href;
if (import.meta.url === _entry) {
  const plaintext = process.argv[2];
  const pk = process.env.SEAL_PK_B64;
  if (!plaintext) {
    console.error("用法: SEAL_PK_B64=<公钥> node encrypt_field.mjs <明文>");
    process.exit(2);
  }
  if (!pk) {
    console.error("错误: 缺少环境变量 SEAL_PK_B64 (公钥)");
    process.exit(2);
  }
  const ct = await encryptField(plaintext, pk);
  console.log(ct);
  if (process.argv.includes("--envelope")) {
    console.log();
    console.log("# 完整 EnvelopeIn (可直接 POST 给 FC):");
    console.log(JSON.stringify(await buildEnvelope(plaintext, pk), null, 2));
  }
}
