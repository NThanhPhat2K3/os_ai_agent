# os_ai_agent: một chuẩn chung cho AI agent

Repo này là **nguồn sự thật duy nhất** về cách Phát dùng AI agent (Claude Code + Codex CLI).
Máy chỉ chứa **symlink** trỏ về đây: sửa một chỗ, cả hai agent cùng đổi.

Thiết kế do Claude đề xuất, Codex phản biện (24/11/2026). Các điều kiện Codex đặt ra đã được áp dụng:
symlink cả thư mục skill, opensource pin phiên bản, Serena và basic-memory mặc định tắt,
installer có dry-run/backup/rollback, memory nằm ngoài git.

> Một nguồn **không** bảo đảm hai agent hành xử giống hệt nhau. Nó chỉ bảo đảm chúng đọc cùng một bộ luật.

## Cấu trúc

| Đường dẫn | Nội dung | Được link tới |
|---|---|---|
| `global/AGENTS.md` | Luật chung cấp người dùng | `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` |
| `skills/ask-claude/` | Codex → Claude (`claude -p`, chỉ đọc) | `~/.claude/skills/`, `~/.agents/skills/` |
| `skills/ask-codex-live/` | Claude → session Codex đang mở (`codex queue`), em xem realtime | như trên |
| `vendor/superpowers/` | `obra/superpowers` (MIT), submodule **pin commit 22f0b46** | 3 skill được chọn, như trên |
| `safety/codex/embedded-safety.rules` | Codex: cấm eFuse, hỏi trước khi flash | `~/.codex/rules/` |
| `safety/claude/permissions.json` | Claude: luật tương đương | merge vào `~/.claude/settings.json` |
| `mcp/servers.toml` | Danh mục MCP + phiên bản pin (tài liệu, client không đọc file này) | được `install.sh` dùng |
| `templates/project/` | `AGENTS.md`, `.clangd`, `docs/decisions.md` mẫu cho dự án | copy thủ công |
| `scripts/` | `install.sh`, `doctor.sh`, `uninstall.sh` | — |

## Opensource đang dùng

| Công cụ | Trạng thái | Vì sao |
|---|---|---|
| Context7 (`upstash/context7`) | **Bật** cho cả hai | Tài liệu thư viện đúng phiên bản. Vẫn phải đối chiếu header/SDK thật |
| superpowers: `systematic-debugging`, `test-driven-development`, `verification-before-completion` | **Bật chọn lọc** | Bộ ba khép kín. `writing-plans` kéo theo 3 skill khác nên chưa bật |
| Serena (`serena-agent==2.1.0`) | Tùy chọn: `--with-serena` | Điều hướng code qua clangd. Cần `compile_commands.json` |
| basic-memory (`basic-memory==1.0.0`) | Tùy chọn: `--with-basic-memory` | Trí nhớ chung. Dữ liệu ở `~/agent-memory` (ngoài git, quyền 700) |

## Cài đặt

```bash
git submodule update --init          # lấy superpowers đúng commit đã pin
scripts/install.sh --dry-run         # xem trước, không thay đổi gì
scripts/install.sh                   # cài
scripts/doctor.sh                    # kiểm tra
# tùy chọn (cần cài uv trước):
scripts/install.sh --with-serena --with-basic-memory
```

Sau khi cài, **khởi động lại Claude Code và Codex**.

Gỡ: `scripts/uninstall.sh [--dry-run]`. Script chỉ hoàn tác những gì `install.sh` đã ghi trong ledger
(`~/.local/state/os_ai_agent/ledger.txt`) và khôi phục bản backup.

## Dùng cho một dự án mới

```bash
cp ~/Desktop/00.Developer/02.skill/os_ai_agent/templates/project/AGENTS.md .
ln -s AGENTS.md CLAUDE.md
mkdir -p docs && cp .../templates/project/docs/decisions.md docs/
cp .../templates/project/.clangd .   # nếu là C/C++; chạy clangd với --query-driver cho cross-compiler
```

## Thêm công cụ mới (quy trình chuẩn)

1. Có một vấn đề cụ thể mà công cụ giải quyết. Không cài "cho đủ bộ".
2. Chọn repo chính chủ hoặc phổ biến và còn bảo trì. Pin phiên bản phát hành **ít nhất 2 tuần**.
3. Ghi vào `mcp/servers.toml` hoặc `install.sh`, mặc định tắt.
4. Hỏi agent còn lại phản biện (skill `ask-codex-live` / `ask-claude`).
5. Thử trên một dự án, chạy `doctor.sh`, rồi mới bật mặc định.

## Giới hạn đã biết

- Luật theo tiền tố (Codex rules, Claude permissions) có thể bị lách bằng wrapper hoặc script. Muốn an toàn thật cho thiết bị thì cần quyền ở mức hệ điều hành (nhóm `dialout`, udev).
- Codex rules đang ở mức *experimental*.
- Rollout log của Codex có thể chứa bí mật: không copy vào memory hay git.
