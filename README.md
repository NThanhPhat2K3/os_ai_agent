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

### 1. Hệ điều hành

| Hệ điều hành | Hỗ trợ |
|---|---|
| **Linux** (đã kiểm thử: Ubuntu) | ✅ Chạy thẳng |
| **Windows** | ✅ Qua **WSL2** (Ubuntu). Làm mọi bước trong terminal WSL, không dùng PowerShell |
| **macOS** | ⚠️ Cần GNU tools vì script dùng `tac`, `sha256sum`, bash ≥ 4: `brew install bash coreutils`, rồi thêm `$(brew --prefix coreutils)/libexec/gnubin` vào đầu `PATH`. Chưa kiểm thử |

### 2. Cài công cụ nền (máy trắng)

Bỏ qua dòng nào máy đã có. Kiểm tra trước bằng lệnh ở cột cuối.

| Công cụ | Cài (Ubuntu/WSL) | Kiểm tra |
|---|---|---|
| git, Python 3.10+, curl | `sudo apt update && sudo apt install -y git python3 curl` | `git --version`, `python3 --version` |
| Node.js ≥ 18 + npm | `sudo apt install -y nodejs npm` (nếu bản apt quá cũ, cài Node LTS bằng [nvm](https://github.com/nvm-sh/nvm)) | `node --version` |
| **Claude Code** | `curl -fsSL https://claude.ai/install.sh \| bash` (hoặc `npm install -g @anthropic-ai/claude-code`) | `claude --version` |
| **Codex CLI** | `npm install -g @openai/codex` | `codex --version` |
| GitHub CLI `gh` | `sudo apt install -y gh` | `gh --version` |
| `uv` (chỉ cho Serena/basic-memory) | xem [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) | `uv --version` |
| Công cụ C/C++ (cho dự án embedded) | `sudo apt install -y clangd clang-tidy cppcheck bear` | `clangd --version` |

Cần ít nhất một trong hai agent. Thiếu cái nào thì installer bỏ qua phần của cái đó và báo rõ.

### 3. Đăng nhập và cấu hình git

```bash
claude                      # lần đầu chạy sẽ hướng dẫn đăng nhập; xong gõ /exit
codex login                 # đăng nhập bằng tài khoản ChatGPT (hoặc API key)
gh auth login               # GitHub.com → HTTPS → đăng nhập bằng trình duyệt; cho phép git dùng thông tin này
git config --global user.name  "NThanhPhat2K3"
git config --global user.email "<email GitHub của em>"
```
Bước `gh auth login` và cấu hình git là **bắt buộc nếu muốn push** từ máy này (quy tắc: thêm skill xong phải
commit + push). Máy công ty nên dùng email cá nhân cho repo này, không dùng email công ty.

### 4. Clone (nhớ lấy cả submodule)

```bash
gh repo clone NThanhPhat2K3/os_ai_agent ~/os_ai_agent -- --recurse-submodules
# hoặc: git clone --recurse-submodules https://github.com/NThanhPhat2K3/os_ai_agent ~/os_ai_agent
cd ~/os_ai_agent
```
Đặt ở đâu cũng được, nhưng **đừng di chuyển hay xóa thư mục sau khi cài**: các symlink trỏ vào đây.
Lỡ clone thiếu submodule thì chạy `git submodule update --init`.

### 5. Chạy thử, rồi cài

```bash
scripts/install.sh --dry-run          # xem trước: in ra mọi thay đổi, chưa làm gì
scripts/install.sh                    # cài thật (thêm --no-context7 nếu công ty không cho)
scripts/doctor.sh                     # mong đợi: "0 problem(s)"
```
Tùy chọn: `--with-token-tools` (ccusage + tokscale), `--with-serena`, `--with-basic-memory` (cần `uv`).

### 6. Phần phải làm tay

1. **Khởi động lại Claude Code và Codex** để chúng nạp luật, skill và rules mới.
2. Plugin Codex cho Claude (để Claude gọi được Codex): trong Claude Code gõ
   ```
   /plugin marketplace add openai/codex-plugin-cc
   /plugin install codex@openai-codex
   /codex:setup
   ```
3. Kiểm tra: hỏi Codex *"bạn có những skill nào?"*. Phải thấy các skill có `codex` trong `skills.json` (hiện 15).

### 7. Checklist: thế nào là xong ✅

- [ ] `scripts/doctor.sh` kết thúc bằng `0 problem(s)`.
- [ ] `python3 -m unittest` báo `OK`.
- [ ] Mở Claude Code: gõ `/skills` (hoặc hỏi *"bạn có những skill nào?"*) thấy các skill dành cho Claude (hiện 12).
- [ ] Mở **session Codex mới**: hỏi *"bạn có những skill nào?"* thấy các skill dành cho Codex (hiện 15).
- [ ] Thử chặn an toàn: nhờ Claude chạy `espefuse.py --version`, phải bị **từ chối**.
- [ ] Claude gọi được Codex: gõ `/codex:review` trong một repo bất kỳ.
- [ ] Codex gọi được Claude: trong Codex nói *"dùng skill ask-claude hỏi Claude 1+1 bằng mấy"*.
- [ ] `scripts/report --no-network` mở được Agent Hub.
- [ ] `git push` từ máy này được (thử `git push --dry-run`).

### 8. Gỡ (nếu cần)

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
| `embedded-systems` (Jeffallan/claude-skills, MIT, 12.5k★) | Bật | Firmware MCU, RTOS, ngắt, DMA, tiết kiệm năng lượng (STM32, ESP32, FreeRTOS) |
| `modern-cpp` (trailofbits/skills, CC-BY-SA-4.0, 8.4k★) | Bật | C++ hiện đại hướng an toàn. Luôn theo chuẩn C++ của dự án (embedded thường C++11/14/17) |
| `karpathy-guidelines` (multica-ai/andrej-karpathy-skills, MIT, 235k★) | Bật | Chống lỗi hay gặp của AI: làm quá tay, sửa lan man, giả định ngầm |
| **OpenAI** `security-best-practices`, `security-threat-model` (openai/skills, Apache-2.0) | Bật | Rà soát bảo mật theo ngôn ngữ/framework, lập threat model |
| **OpenAI** `gh-fix-ci`, `gh-address-comments` | Bật | Sửa CI GitHub Actions bị lỗi, xử lý comment review trên PR (dùng `gh` với tài khoản của bạn) |
| **Anthropic** `mcp-builder` (anthropics/skills, Apache-2.0) | Bật | Viết MCP server chất lượng (Python/TypeScript) |
| **Anthropic** `pdf`, `docx`, `xlsx`, `pptx` | **Chỉ Codex** | Đọc/tạo PDF (datasheet!), Word, Excel, PowerPoint. Claude đã có sẵn bản đồng bộ từ claude.ai nên không link cho Claude |

Trường `agents` trong `skills.json` chọn skill dành cho agent nào: `ask-claude` chỉ cho Codex, `ask-codex-live` chỉ cho
Claude. Skill có `notes` (cảnh báo đã biết) được hiển thị màu cam trong Agent Hub.
| Context7 (`upstash/context7`) | Bật (tắt bằng `--no-context7`) | Tài liệu thư viện đúng phiên bản. Vẫn phải đối chiếu header/SDK thật |
| ccusage, tokscale | Tùy chọn `--with-token-tools` | Báo cáo / dashboard token, offline, tắt telemetry, ẩn cột tiền |
| Serena, basic-memory | Tùy chọn | Điều hướng code qua clangd; trí nhớ chung ở `~/agent-memory` (ngoài git) |
| skills CLI (`vercel-labs/skills`) | Chỉ theo dõi | Bản đủ tuổi chưa pin được commit |

## ➕ Thêm hoặc gỡ skill

```bash
scripts/add-skill owner/repo ten-skill --dry-run   # kiểm tra SKILL.md, trùng tên, phụ thuộc, code đi kèm
scripts/add-skill owner/repo ten-skill             # submodule pin commit ≥14 ngày + ghi skills.json
scripts/add-skill --remove ten-skill
scripts/add-skill owner/repo ten-skill --agents codex   # chỉ cài cho một agent
```
Quy trình: đọc SKILL.md → `scripts/doctor.sh` → nhờ agent còn lại review → `scripts/install.sh` → **commit và push ngay**:
```bash
git add -A && git commit -m "Add skill ten-skill" && git push
```
> 📌 **Luôn commit + push sau khi thêm, gỡ hay cập nhật skill**, để máy khác chỉ cần `git pull`.
> Repo đang **public**: trước khi push, xem lại `git diff --cached` và đảm bảo không có bí mật, API key hay code công ty.
Nguồn uy tín: `anthropics/skills`, `openai/skills` (skill nằm ở `skills/.curated`), `obra/superpowers`, `trailofbits/skills`, `Jeffallan/claude-skills`,
`addyosmani/agent-skills`, `hesreallyhim/awesome-claude-code`, skills.sh.
Repo để mỗi skill trong một thư mục plugin riêng (như Trail of Bits) thì dùng `--skills-dir plugins/<tên>/skills`.
Nếu bị báo *no SKILL.md at the pinned commit*: cấu trúc repo 14 ngày trước khác bây giờ, xem bằng
`gh api "repos/OWNER/REPO/git/trees/<sha>?recursive=1" --jq '.tree[].path' | grep SKILL.md`.

## 🔄 Cập nhật

Phiên bản nằm ở `pins.json` và commit của các submodule trong `vendor/`. Không có gì tự cập nhật.
1. `scripts/check-updates` (hoặc tab Cập nhật) để xem đề xuất.
2. Sửa `pins.json`, hoặc `git -C vendor/<repo> checkout <sha>`.
3. `scripts/doctor.sh`, nhờ agent còn lại review, `scripts/install.sh` (với token tools: `--with-token-tools`), rồi **commit và push**.

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

## 🆘 Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| `vendor/superpowers` rỗng, doctor báo `SKILL.md missing` | `git submodule update --init` rồi chạy lại `scripts/install.sh` |
| `Permission denied` khi chạy `scripts/...` | `chmod +x scripts/*` (thường do copy file thay vì `git clone`) |
| Codex không thấy skill / rules mới | **Mở session Codex mới** (session cũ không nạp lại). Kiểm tra `ls -l ~/.agents/skills` |
| Claude không thấy skill | Thoát và mở lại Claude Code; kiểm tra `ls -l ~/.claude/skills` |
| doctor báo `not linked` sau khi chuyển thư mục repo | Đừng di chuyển repo. Nếu đã lỡ: `scripts/install.sh` lại ở vị trí mới (link cũ sẽ được backup) |
| doctor báo `stale link` | Skill đã bị gỡ khỏi `skills.json`: `rm` các symlink được báo (chúng chỉ là link) |
| `install.sh` báo `conflict ... backup to` | Bình thường: file cũ được cất vào `~/.local/state/os_ai_agent/backups/`, xem lại nếu cần |
| `codex: 'idf.py ...' → allow-default` sai mong đợi | Rules chưa được link: `ls -l ~/.codex/rules/`; chạy lại `scripts/install.sh` |
| `scripts/tokens` báo chưa cài / lệch phiên bản | `scripts/install.sh --with-token-tools` |
| `check-updates` báo `lỗi` | Mất mạng hoặc bị giới hạn GitHub API: `gh auth login` rồi chạy lại |
| `git push` bị từ chối | `gh auth login` (chọn cho git dùng thông tin đăng nhập), rồi `git pull --rebase` và push lại |
| macOS: `tac: command not found` / lỗi `declare -A` | Xem mục 1: cài `bash` và `coreutils` bằng Homebrew |

Vẫn không được: chạy `scripts/doctor.sh`, dán toàn bộ output cho agent và nhờ nó đọc `AGENTS.md` để chẩn đoán.

## ⚠️ Giới hạn đã biết

- Luật theo tiền tố (Codex rules, Claude permissions) có thể bị lách bằng wrapper hoặc script. An toàn thật cho
  thiết bị cần quyền ở mức hệ điều hành (nhóm `dialout`, udev).
- Codex rules đang ở mức *experimental*; định dạng log Codex/Claude có thể đổi theo phiên bản.
- Rollout log của Codex và log của Claude có thể chứa bí mật: không copy vào memory hay git.
- Lượt Codex chạy qua `codex queue` hay dừng sớm với việc build lớn; hợp với review. Việc lớn nên gõ trực tiếp vào Codex.
