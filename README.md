# os_ai_agent: một chuẩn chung cho AI agent

Repo này là **nguồn sự thật duy nhất** về cách Phát dùng AI agent (Claude Code + Codex CLI).
Máy chỉ chứa **symlink** trỏ về repo: sửa một chỗ, cả hai agent cùng đổi.

- Luật chung, skill dùng chung, luật an toàn phần cứng (flash/eFuse), MCP, mẫu dự án.
- Giao diện **Agent Hub** (`scripts/report`): skill, cập nhật, token.
- Mọi thay đổi do Claude build và Codex review (hoặc ngược lại), có test.

> Một nguồn **không** bảo đảm hai agent hành xử giống hệt nhau. Nó chỉ bảo đảm chúng đọc cùng một bộ luật.

---

## 🚀 Cài trên máy mới (ví dụ máy công ty)

> **Nhờ AI agent cài?** Mở Claude Code hoặc Codex **trong thư mục repo** và nói:
> *"Đọc AGENTS.md và cài đặt repo này cho tôi."* File `AGENTS.md` ở gốc repo là hướng dẫn dành riêng cho agent:
> nó sẽ kiểm tra máy, chạy thử trước, hỏi bạn trước những bước quan trọng, rồi cài và kiểm tra.

### 0. Trước khi cài trên máy công ty

- **Đọc chính sách IT/bảo mật của công ty** về công cụ AI và phần mềm bên thứ ba. Nếu không chắc, hỏi IT trước.
- **Context7** gửi câu hỏi về thư viện (có thể kèm đoạn code) tới server `mcp.context7.com`. Nếu công ty không cho
  phép gửi code ra ngoài, cài với `--no-context7`.
- **Token tools** (ccusage/tokscale) đọc log hội thoại trên máy để đếm token, chạy offline. Đây là tùy chọn.
- Nếu máy đã có `~/.claude/CLAUDE.md` hoặc `~/.codex/AGENTS.md` (ví dụ luật của công ty), installer sẽ **backup rồi
  thay bằng symlink**. Hãy xem nội dung cũ trước, và gộp những luật cần giữ vào `global/AGENTS.md` (hoặc dùng luật
  cấp dự án) thay vì để mất.

### 1. Yêu cầu

| Công cụ | Bắt buộc? | Kiểm tra |
|---|---|---|
| git | ✅ | `git --version` |
| Python ≥ 3.10 | ✅ | `python3 --version` |
| Claude Code và/hoặc Codex CLI, đã đăng nhập | ✅ (ít nhất một) | `claude --version`, `codex --version` |
| Node.js ≥ 18 + npm | Cho Context7 phía Codex và token tools | `node --version` |
| GitHub CLI `gh` (đã `gh auth login`) | Nên có (clone repo private, tránh giới hạn API) | `gh auth status` |
| `uv` | Chỉ khi dùng Serena / basic-memory | `uv --version` |
| clangd, clang-tidy, cppcheck, bear | Cho dự án C/C++ | `sudo apt install clangd clang-tidy cppcheck bear` |

### 2. Clone (nhớ lấy cả submodule)

```bash
gh repo clone NThanhPhat2K3/os_ai_agent ~/os_ai_agent -- --recurse-submodules
# hoặc: git clone --recurse-submodules https://github.com/NThanhPhat2K3/os_ai_agent ~/os_ai_agent
cd ~/os_ai_agent
```
Đặt ở đâu cũng được, nhưng **đừng di chuyển hay xóa thư mục sau khi cài**: các symlink trỏ vào đây.
Lỡ clone thiếu submodule thì chạy `git submodule update --init`.

### 3. Chạy thử, rồi cài

```bash
scripts/install.sh --dry-run          # xem trước: in ra mọi thay đổi, chưa làm gì
scripts/install.sh                    # cài thật (thêm --no-context7 nếu công ty không cho)
scripts/doctor.sh                     # mong đợi: "0 problem(s)"
```
Tùy chọn: `--with-token-tools` (ccusage + tokscale), `--with-serena`, `--with-basic-memory` (cần `uv`).

### 4. Phần phải làm tay

1. **Khởi động lại Claude Code và Codex** để chúng nạp luật, skill và rules mới.
2. Plugin Codex cho Claude (để Claude gọi được Codex): trong Claude Code gõ
   ```
   /plugin marketplace add openai/codex-plugin-cc
   /plugin install codex@openai-codex
   /codex:setup
   ```
3. Kiểm tra: hỏi Codex *"bạn có những skill nào?"*. Phải thấy `ask-claude`, `ask-codex-live`,
   `systematic-debugging`, `test-driven-development`, `verification-before-completion`.

### 5. Gỡ (nếu cần)

```bash
scripts/uninstall.sh --dry-run    # xem trước
scripts/uninstall.sh              # chỉ hoàn tác đúng những gì install.sh đã làm, khôi phục bản backup
```
Ledger và backup nằm ở `~/.local/state/os_ai_agent/`. Mục nào bạn đã sửa tay sau khi cài sẽ được **giữ nguyên** và báo lại.

---

## 🗂️ Cấu trúc

| Đường dẫn | Nội dung | Được link / dùng ở |
|---|---|---|
| `AGENTS.md` (+ `CLAUDE.md`) | Hướng dẫn cho agent khi làm việc **trong repo này** (cài đặt, quy ước) | Agent tự đọc khi mở repo |
| `global/AGENTS.md` | Luật chung cấp người dùng cho mọi dự án | `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` |
| `skills.json` | **Danh mục skill duy nhất** | `install.sh`, `doctor.sh`, `check-updates`, `report` |
| `skills/<tên>/` | Skill tự viết (`ask-claude`, `ask-codex-live`) | `~/.claude/skills/`, `~/.agents/skills/` |
| `vendor/<repo>/` | Skill bên thứ ba, git submodule **pin theo commit** | như trên (chỉ các skill có trong `skills.json`) |
| `pins.json` | **Phiên bản duy nhất** của tool npm/PyPI | `install.sh`, `tokens`, `check-updates` |
| `safety/codex/embedded-safety.rules` | Codex: cấm eFuse, hỏi trước khi flash/debug | `~/.codex/rules/` |
| `safety/claude/permissions.json` | Claude: luật tương đương | merge vào `~/.claude/settings.json` |
| `mcp/servers.toml` | Tài liệu về các MCP server (client không đọc file này) | — |
| `templates/project/` | `AGENTS.md`, `.clangd`, `docs/decisions.md` mẫu cho dự án mới | copy thủ công |
| `tools/skill_hub/` | Code Python dùng chung (catalog, engine kiểm tra cập nhật) | các script |
| `scripts/` | `install.sh`, `doctor.sh`, `uninstall.sh`, `report`, `add-skill`, `check-updates`, `tokens` | — |
| `tests/` | `python3 -m unittest` | — |

## 🧰 Lệnh hằng ngày

| Lệnh | Làm gì |
|---|---|
| `scripts/report` | Mở **Agent Hub** trên trình duyệt (tab Skill / Cập nhật / Token / Thêm skill) |
| `scripts/doctor.sh` | Kiểm tra sức khỏe toàn bộ setup |
| `scripts/check-updates` | Skill/tool nào có bản mới (không đề xuất bản < 14 ngày, không bao giờ hạ cấp) |
| `scripts/tokens` / `tokens weekly` / `tokens tui` | Token Claude + Codex (cần `--with-token-tools`) |
| `scripts/add-skill owner/repo ten-skill --dry-run` | Thử thêm một skill |

## 🧩 Skill và opensource đang dùng

| Thành phần | Trạng thái | Vì sao |
|---|---|---|
| `ask-claude`, `ask-codex-live` | Bật (tự viết) | Claude ⇄ Codex gọi nhau; `ask-codex-live` gửi vào session Codex đang mở để bạn xem realtime |
| superpowers: `systematic-debugging`, `test-driven-development`, `verification-before-completion` | Bật chọn lọc | Bộ ba khép kín. `writing-plans` kéo theo 3 skill khác nên chưa bật |
| Context7 (`upstash/context7`) | Bật (tắt bằng `--no-context7`) | Tài liệu thư viện đúng phiên bản. Vẫn phải đối chiếu header/SDK thật |
| ccusage, tokscale | Tùy chọn `--with-token-tools` | Báo cáo / dashboard token, offline, tắt telemetry, ẩn cột tiền |
| Serena, basic-memory | Tùy chọn | Điều hướng code qua clangd; trí nhớ chung ở `~/agent-memory` (ngoài git) |
| skills CLI (`vercel-labs/skills`) | Chỉ theo dõi | Bản đủ tuổi chưa pin được commit |

## ➕ Thêm hoặc gỡ skill

```bash
scripts/add-skill owner/repo ten-skill --dry-run   # kiểm tra SKILL.md, trùng tên, phụ thuộc, code đi kèm
scripts/add-skill owner/repo ten-skill             # submodule pin commit ≥14 ngày + ghi skills.json
scripts/add-skill --remove ten-skill
```
Quy trình: đọc SKILL.md → `scripts/doctor.sh` → nhờ agent còn lại review → commit → `scripts/install.sh` → push.
Nguồn uy tín: `anthropics/skills`, `obra/superpowers`, `hesreallyhim/awesome-claude-code`, skills.sh.

## 🔄 Cập nhật

Phiên bản nằm ở `pins.json` và commit của các submodule trong `vendor/`. Không có gì tự cập nhật.
1. `scripts/check-updates` (hoặc tab Cập nhật) để xem đề xuất.
2. Sửa `pins.json`, hoặc `git -C vendor/<repo> checkout <sha>`.
3. `scripts/doctor.sh`, nhờ agent còn lại review, commit, `scripts/install.sh` (với token tools: `--with-token-tools`).

**Đồng bộ giữa các máy:** máy nào sửa thì commit + push; máy khác chỉ cần
`git pull --recurse-submodules && scripts/install.sh && scripts/doctor.sh`.

## 📁 Dùng cho một dự án mới

```bash
HUB=$(dirname "$(dirname "$(readlink -f ~/.codex/AGENTS.md)")")   # vị trí repo này
cp "$HUB/templates/project/AGENTS.md" . && ln -s AGENTS.md CLAUDE.md
mkdir -p docs && cp "$HUB/templates/project/docs/decisions.md" docs/
cp "$HUB/templates/project/.clangd" .   # C/C++: chạy clangd với --query-driver cho cross-compiler
```

## 🧪 Phát triển repo này

- Test: `python3 -m unittest`. Kiểm tra cài/gỡ an toàn trên HOME giả: `HOME=$(mktemp -d) scripts/install.sh`.
- Thêm công cụ: phải giải quyết một vấn đề cụ thể; repo chính chủ hoặc phổ biến, còn bảo trì; pin bản ≥ 14 ngày;
  mặc định tắt; nhờ agent còn lại phản biện; thử trên một dự án rồi mới bật.
- Lịch sử thiết kế: `docs/specs/`.

## ⚠️ Giới hạn đã biết

- Luật theo tiền tố (Codex rules, Claude permissions) có thể bị lách bằng wrapper hoặc script. An toàn thật cho
  thiết bị cần quyền ở mức hệ điều hành (nhóm `dialout`, udev).
- Codex rules đang ở mức *experimental*; định dạng log Codex/Claude có thể đổi theo phiên bản.
- Rollout log của Codex và log của Claude có thể chứa bí mật: không copy vào memory hay git.
- Lượt Codex chạy qua `codex queue` hay dừng sớm với việc build lớn; hợp với review. Việc lớn nên gõ trực tiếp vào Codex.
