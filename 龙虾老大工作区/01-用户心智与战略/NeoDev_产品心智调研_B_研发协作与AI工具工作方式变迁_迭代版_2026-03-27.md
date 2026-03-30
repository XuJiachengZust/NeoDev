# NeoDev 产品心智调研 B（迭代版）：AI 开发工具、研发协作与文档/项目系统如何改变用户工作方式和心智

日期：2026-03-27
研究方式：规划 → 执行 → 审查 → 反思 → 补调研（已完成至少一轮显式自审与修订）
目标：围绕 GitHub、Linear、Notion、Figma、Cursor、Vercel、Jira 等产品，分析它们如何建立用户认知、改变工作习惯，并提炼对 NeoDev 的可迁移策略与风险。

---

# 0. 执行说明

这不是一次性草稿，而是按迭代研究流程完成的阶段性交付。

本稿包含：
1. 研究框架（先定义怎么研究）
2. 第一轮调研结论
3. 自我审查与缺口识别
4. 第二轮补调研与修订后的结论
5. NeoDev 可迁移策略与风险
6. 本轮研究局限与建议的下一轮问题

这样做的目的是避免“只列观点、不校验结构、不补证据”。

---

# 1. 研究框架（规划阶段）

## 1.1 研究问题

本次不只问“这些产品有什么功能”，而是问四个更关键的问题：

1. **它们在用户脑中建立了什么默认认知？**
   也就是用户会开始认为：“这类工作本来就应该这样做。”

2. **它们改变了哪些具体工作习惯？**
   例如从发附件到发链接、从长文档到短 issue、从手工执行到 AI 编排。

3. **它们靠什么机制让这种习惯稳定下来？**
   是功能设计、默认流程、方法论教育、组织扩散，还是可见结果？

4. **哪些机制可以迁移到 NeoDev，哪些不能？**
   不能只做产品致敬，必须识别可复制和不可复制部分。

## 1.2 观察维度

为避免只停留在“产品印象”，我用 6 个统一维度看每个产品：

1. **核心心智定位**：它想让用户怎么理解自己
2. **默认工作对象**：系统里的核心对象是什么（issue、PR、page、preview、agent task 等）
3. **习惯改写点**：用户行为被改写在哪里
4. **机制抓手**：是什么产品设计促成这种习惯改变
5. **扩散逻辑**：这套方式如何从个人扩散到团队/组织
6. **对 NeoDev 的迁移价值**：可借鉴之处与限制

## 1.3 初始假设

在正式调研前，我先给出三个假设，后续再验证：

### 假设 A
头部研发协作产品的竞争核心，不是功能多，而是**定义默认工作流**。

### 假设 B
AI 时代的关键迁移，不是“自动化更多步骤”，而是**把人的角色从执行者迁移为编排者、判断者、验收者**。

### 假设 C
NeoDev 的潜在机会，不在于再做一个任务工具，而在于**把 AI 参与研发后断裂的链路重新接起来**。

---

# 2. 第一轮调研（执行阶段：Round 1）

第一轮调研主要使用官网、官方文档、官方博客与方法论文档，优先建立“产品自我定义”和“方法论表述”的基础图谱。

## 2.1 GitHub：把开发工作的事实源固定在代码上下文里

### 核心心智
GitHub 建立的是：
**开发协作应尽量围绕代码与代码相关对象展开。**

### 证据点
- GitHub Issues 强调 issue、sub-issue、custom fields、projects、automations
- 官方文案反复强调 planning close to code
- 讨论、提交、PR、发布、部署可互相引用，形成同一时间线

### 改变的习惯
- 任务不再只是 PM 表格里的行，而是和代码活动连在一起的对象
- 状态同步越来越由系统对象暴露，而不是靠人口头汇报
- 开发者更自然地在仓库周边完成讨论、拆解、评审、追溯

### 初步判断
GitHub 最强的地方不是某个单功能，而是把“工作证据”收敛在开发上下文内。

---

## 2.2 Linear：把高质量、低噪音、高速度执行做成一种纪律

### 核心心智
Linear 卖的不是 issue tracker 本身，而是：
**一种讲究 clarity、momentum、small scope 的产品开发纪律。**

### 证据点
- 官方 Method 明确写出 Principles & Practices
- 明确主张：Build for creators、Create momentum、Simple first then powerful、Say no to busy work
- 明确反对 user stories，主张短 issue、直接表达
- 强调项目 1–3 周、小团队、连续出货、用实际工作衡量进展

### 改变的习惯
- 从长用户故事转向短而可执行的 issue
- 从“先把流程设计完整”转向“先建立 momentum”
- 从大项目执念转向 scope down
- 从管理者层层拆任务转向执行者自己写 issue、自己承担 owner 责任

### 初步判断
Linear 改写的不只是工具使用方式，而是团队对“好执行”长什么样的审美。

---

## 2.3 Notion：把 connected workspace 变成默认期待

### 核心心智
Notion 的默认认知是：
**知识、文档、项目、数据库、AI 应该在同一个工作空间里联动。**

### 证据点
- 官方 product/projects 页面持续强调 single place / connected workspace
- 任务页面承载上下文
- OpenAI 客户案例中，Notion 被定义为 centralized place for how teams work
- OpenAI 将研究、工程、GTM 的知识与流程放进同一团队空间，辅以 AI 搜索和问答

### 改变的习惯
- 从文件夹思维转向对象/页面/数据库思维
- 从“文档是附件”转向“文档是执行上下文的一部分”
- 从知识零散沉淀转向组织级知识中枢
- 从局部记录转向跨团队共享与复用

### 初步判断
Notion 的心智影响力来自“统一工作中枢”而不是单点功能深度。

---

## 2.4 Figma：把设计从交付文件改成共享空间

### 核心心智
Figma 最深的改变是：
**设计不再是设计师私有文件，而是跨角色共享、实时更新的工作空间。**

### 证据点
- 官方多人协作技术博客强调 live collaborative editing 取代导出/同步/邮件副本
- Dev Mode 明确定位为更适合开发者的工作区，借鉴浏览器 DevTools 心智
- 通过 GitHub/Jira/Linear/Storybook 等连接设计与开发上下文

### 改变的习惯
- 从“设计完成后交付”转向“设计过程可被参与”
- 从“看截图/切图”转向“看同一份在线设计”
- 从 handoff 转向 shared context
- 从静态规范转向与代码、任务、设计系统联动

### 初步判断
Figma 不是优化 handoff，而是在削弱 handoff 本身。

---

## 2.5 Cursor：把程序员推向 AI 协同编排者

### 核心心智
Cursor 最强的心智位是：
**软件开发正在从“人逐行写”转向“人定义任务、AI 理解代码库并执行”。**

### 证据点
- 首页强调 autonomy slider、agent、parallel、end-to-end review
- 官方 best practices 强调 plan mode、context management、rules、skills、hooks
- Salesforce 客户案例提到：日常使用快速扩散，速度、质量、吞吐都有 double-digit 提升
- 自研研究文章强调多 agent、planner/worker 结构、反思、freshness、handoff

### 改变的习惯
- 从直接编码转向先规划再执行
- 从人手动搜上下文转向 agent 主动找上下文
- 从人亲自做全部重复劳动转向人保留判断权
- 从“会写代码”转向“会定义目标、边界、验收标准并审核结果”

### 初步判断
Cursor 不只是提供 AI 能力，而是在教育用户如何与 agent 协作。

---

## 2.6 Vercel：把部署变成协作界面

### 核心心智
Vercel 建立的是：
**每次变更都应该自动生成一个可访问、可评论、可分享的结果。**

### 证据点
- 官方 environments 文档清晰定义 local / preview / production
- Preview deployment 默认随分支、PR、非生产提交生成
- Comments 可直接挂在 preview 上
- 客户案例大多讲更快迭代、发布更稳、构建更快、开发者更开心

### 改变的习惯
- 从“开发完统一测试”转向“每次改动都有预览”
- 从截图讨论转向在真实运行界面评论
- 从上线大爆炸转向预览—验证—推广的连续流
- 从本地结果不可见转向结果可分享

### 初步判断
Vercel 最值得学的不是部署技术本身，而是“结果可见即协作入口”。

---

## 2.7 Jira：把复杂组织的流程治理产品化

### 核心心智
Jira 核心不是轻，而是：
**复杂组织需要显式流程、权限、依赖、报表和自动化来维持协作秩序。**

### 证据点
- Atlassian 官方强调 workflows、permissions、custom fields、reports、goals、dependencies、AI automation
- 叙事面向 every team，但底层能力更像组织治理引擎

### 改变的习惯
- 让团队习惯显式定义流程状态
- 让管理层习惯用系统看容量、风险、进度
- 让组织默认接受“流程设计本身是协作成本的一部分”

### 初步判断
Jira 的价值在组织规模化与治理，而不是轻巧体验。

---

# 3. 第一轮结论（阶段性总结）

第一轮之后，我得到一个初步结构化结论：

## 3.1 这些产品共同改变了六种习惯

1. 从**附件交付**转向**链接协作**
2. 从**人工汇报状态**转向**对象自动暴露状态**
3. 从**角色 handoff**转向**共享上下文协作**
4. 从**写长说明**转向**写可执行对象**
5. 从**手工推进**转向**设约束 + 自动推进**
6. 从**执行者**转向**定义目标与验收的人**

## 3.2 对 NeoDev 的初步机会判断

NeoDev 更可能占据的位置不是：
- 更智能的任务工具
- 更全能的文档平台
- 更自动的编码助手

而是：
**把 AI 参与研发之后的需求、上下文、执行、验收重新接成闭环。**

---

# 4. 自我审查（审查阶段）

第一轮完成后，我对结果做了显式自审，发现至少有 4 个缺口：

## 缺口 1：证据偏“产品自我叙事”，缺少 adoption/组织落地角度

第一轮大量使用官网和方法论页面，能很好看到它们“想让用户怎么理解自己”，但对“这种工作方式如何真正被组织接受并扩散”还不够。

### 影响
会让结论过于概念化，缺少“为什么用户真的会形成习惯”的中间机制。

---

## 缺口 2：对 Cursor 的分析偏能力视角，未充分展开“角色迁移”

第一轮提到了 plan mode、agent、context，但对“程序员角色从执行者向编排者迁移”的组织影响还不够深。

### 影响
对 NeoDev 的启发可能还停留在“加 AI 能力”，而不是“重构团队分工”。

---

## 缺口 3：对 Notion 的论证偏产品页面，缺少真实案例支撑

第一轮已判断 Notion 在建立统一中枢心智，但若没有客户案例，容易看起来像标准 marketing narrative。

### 影响
结论说服力不足，尤其对“知识如何转成组织行动”这一点。

---

## 缺口 4：对 Vercel 的总结偏功能，没有把“可见结果如何替代汇报/截图/会议”说透

第一轮说了 preview 和 comments，但还没有把它抽象成通用工作流模式。

### 影响
对 NeoDev 可迁移策略仍不够锋利。

---

# 5. 第二轮补调研（执行阶段：Round 2）

基于上述缺口，我补了以下方向：
- Linear 方法论原文（Introduction / Scope projects down）
- Notion × OpenAI 客户案例
- Cursor × Salesforce adoption 案例
- Cursor 长时多 agent 研究文章
- Vercel customers / preview / comments 逻辑

补完后，结论有以下增强。

---

## 5.1 修订点一：这些产品不只是提供工具，还在输出“工作法”

第一轮我已经感觉到了这一点；第二轮证据更明确。

### 新证据
- Linear 明确公开 Method，系统化讲 principles & practices
- Cursor 明确公开 best practices，教用户如何与 agents 协作
- Vercel 通过 environments / preview / comments 文档，把“怎么协作”产品化
- Notion 通过客户案例把 centralized workspace 叙事具体化

### 修订后的判断
真正改变用户心智的产品，几乎都在做一件事：
**不仅交付功能，也交付一种推荐工作法。**

这意味着 NeoDev 若想抢心智，不能只发布 feature list，必须输出：
- 什么是 NeoDev 的默认研发闭环
- 什么应该先由 AI 做
- 什么必须由人审
- 什么对象应该天然可追踪

---

## 5.2 修订点二：用户习惯形成，不只是因为效率高，还因为“责任结构被重写”

这点在 Cursor 第二轮调研中更清晰。

### 新证据
- Cursor 的官方 best practices 强调 plan、context、rules、skills，不是鼓励无脑自动执行
- Salesforce 案例中，初级工程师用 Cursor 理解代码库、加速上手；高级工程师先从 boring tasks 建立信任，再扩大使用范围
- 多 agent 研究文章显示：要让 agent 真正推进复杂任务，必须明确 planner / worker / handoff / ownership

### 修订后的判断
AI 工具带来的深层变化，并不是“替用户多做一点”，而是：
**重新划分谁负责理解问题、谁负责执行、谁负责验收。**

对 NeoDev 的含义非常大：
如果 NeoDev 只是“AI 帮你生成内容”，那它只是助手；
如果 NeoDev 帮团队重构责任流和验收流，它才有机会变成工作方式基础设施。

---

## 5.3 修订点三：统一工作中枢的真正价值，不是信息集中，而是减少组织性遗忘

### 新证据
Notion × OpenAI 案例给出一个很重要的视角：
- 技术文档和经验被持续改进（campsite principle）
- 新人、跨时区成员、on-call 人员可通过 Notion AI 快速找回上下文
- 研究、工程、GTM 的知识能流入同一中枢并反哺产品推进

### 修订后的判断
Notion 的价值不只是“all in one”，而是：
**把过去易丢失、易碎片化、难复用的组织知识，变成持续可调用的行动资产。**

这对 NeoDev 的启发是：
NeoDev 不该只保存“任务状态”，更应保存“为什么这么做、引用了什么、验收证据是什么、后续可复用什么”。

---

## 5.4 修订点四：Vercel 的真正范式是“结果先可见，再展开评审”

### 新证据
- Preview deployment 随分支/PR 自动生成
- Comments 直接依附在 preview 上
- 客户案例叙事高度集中在更快迭代、更短构建、更快部署、更有信心地上线

### 修订后的判断
Vercel 的强大之处不是“帮你部署”，而是：
**把原本需要开会、截图、口头解释的事情，压缩成一个可以直接查看和评论的结果对象。**

这是个高度可迁移的模式：
- 需求草案也可以 preview
- 任务拆解也可以 preview
- AI 计划也可以 preview
- 验收证据也可以 preview

对 NeoDev 来说，这比“支持评论”更高一级。

---

# 6. 修订后的最终结论

经过一轮自审和二轮补调研后，我把总体判断修订为以下版本。

## 6.1 头部工具竞争的本质：争夺“默认工作流定义权”

这些产品的真正竞争，不是：
- 谁功能多
- 谁界面更酷
- 谁速度更快

而是：
**谁能让用户逐渐相信：这类工作本来就应该这样发生。**

例如：
- GitHub：开发协作应贴着代码发生
- Linear：执行应短、快、清晰、低噪音
- Notion：知识、项目、AI 应在一个 connected workspace 联动
- Figma：设计不该靠交付文件，而应在共享空间中演化
- Cursor：开发者应先定义计划与边界，再让 agent 执行
- Vercel：每次变更都应该有可见结果用于协作
- Jira：规模化组织需要显式流程治理

---

## 6.2 这些产品共同改写了用户的 4 层心智

### 第一层：对象心智
用户越来越接受：
工作应以可追踪对象存在，而不是散落在聊天和会议里。

### 第二层：上下文心智
用户越来越接受：
好的工作流应该减少工具跳转，让上下文尽量连续。

### 第三层：状态心智
用户越来越接受：
状态应该由系统自动暴露，而不是靠人同步。

### 第四层：角色心智
用户越来越接受：
人不一定亲手做每一步，但必须定义边界、做判断、做验收。

其中第四层，是 AI 时代最关键的新变化。

---

## 6.3 对 NeoDev 的最佳机会位

我现在比第一轮更确定：
NeoDev 最值得抢占的，不是单点能力位，而是链路位。

### 建议定义
**NeoDev 应被定义为：把需求、上下文、执行、证据、验收连接起来的人机协作研发闭环层。**

为什么是这个位置？

因为现在市场上已有：
- 文档中枢（Notion）
- 代码事实源（GitHub）
- 轻项目系统（Linear）
- 设计共享空间（Figma）
- AI 编码执行层（Cursor）
- 预览协作层（Vercel）
- 流程治理层（Jira）

但 **AI 参与研发后，跨这些对象之间的闭环仍很容易断裂**：
- 需求到执行之间断
- 文档到代码之间断
- AI 输出到人工验收之间断
- 决策到证据之间断

NeoDev 可以补这条断裂带。

---

# 7. 对 NeoDev 的可迁移策略（修订版）

## 策略 1：把“目标—边界—上下文—任务—产物—证据—验收”做成一等对象

这是 NeoDev 最值得明确建模的一组对象。

如果这组对象天然联通，NeoDev 的心智会非常清晰：
**不是在管理任务，而是在管理从意图到结果的闭环。**

---

## 策略 2：默认先出计划，再执行；默认先给证据，再求通过

借鉴 Cursor + Vercel：
- AI 不要直接黑箱推进到底
- 先给 plan / scope / assumptions
- 执行后给 diff / artifact / evidence / unresolved risks
- 人做批准与验收

这能同时解决效率与信任问题。

---

## 策略 3：把“共享评审”做成核心场景，而不是附属评论功能

借鉴 Figma + Vercel：
- 需求不是发附件，而是发结构化页面
- 任务拆解不是开会过，而是在线审阅
- AI 结果不是一句“已完成”，而是可查看、可批注、可回溯的结果页
- 验收不是只看状态，而是看证据

NeoDev 若做到这一点，就会天然减少大量 handoff friction。

---

## 策略 4：把“组织知识的沉淀与再调用”做成系统能力

借鉴 Notion × OpenAI：
NeoDev 不应只追踪“现在在做什么”，更应支持：
- 为什么做
- 之前怎么做过
- 哪些方案被否掉了
- 哪些证据支撑当前判断
- 哪些内容可被未来任务复用

这会让 NeoDev 不只是流程工具，而是闭环记忆系统。

---

## 策略 5：前台体验像 Linear/Cursor 一样轻，后台能力像 Jira 一样可治理

这是产品层面的关键平衡。

### 前台应做到
- 快速上手
- 少配置
- 强默认
- 清晰对象关系

### 后台应逐级增强
- 规则模板
- 审批点
- 权限边界
- 审计与指标
- 组织级策略控制

否则 NeoDev 会陷入两难：
- 只轻不稳，进不了组织
- 只稳不轻，起不来 adoption

---

## 策略 6：NeoDev 必须输出自己的工作法内容

借鉴 Linear Method / Cursor Best Practices：
NeoDev 需要自己的方法论资产，例如：
- 什么是一个可执行需求
- 什么是好的 AI 协作分工
- 哪些节点必须人审
- 如何定义 evidence-based acceptance
- 如何避免 AI 在多步骤研发中失控

没有这层工作法，NeoDev 很容易被理解为“一个集成了 AI 的工作台”。

有了这层工作法，它才可能被理解为“AI 时代研发协作的新范式”。

---

# 8. 风险（修订版）

## 风险 1：被当成边缘增强层，而不是默认入口

如果 NeoDev 只在某个环节被偶尔调用，它很难形成习惯性心智。

### 表现
- 需求还在别处定
- 任务还在别处跑
- 代码证据还在别处看
- NeoDev 只负责生成某一段内容

### 应对
先拿下一个高频闭环，而不是一开始求全。

---

## 风险 2：AI 产出强，但不可审、不可追溯、不可验收

这会直接破坏信任。

### 应对
- 每个结果有引用来源
- 每次执行有 plan/diff/evidence
- 关键节点有人审
- 风险与未决项显式列出

---

## 风险 3：概念过大，产品叙事失焦

“研发闭环平台”“AI 工作操作系统”这类表述容易空。

### 应对
先用一个强场景把价值打透，例如：
**从需求到任务拆解到 AI 执行计划到验收证据**

场景先打透，心智才会立住。

---

## 风险 4：只适合小团队，进不了中大组织

### 应对
产品结构必须支持从个人/小队到组织的升级路径，而不是一套体验打天下。

---

## 风险 5：模仿头部产品表层功能，失去独立定位

### 应对
NeoDev 必须用一句足够清晰的话定义自己。

我当前更推荐的定义是：
**NeoDev 把需求、上下文、执行与验收连接成一条可追踪的人机协作研发链路。**

---

# 9. 建议给 NeoDev 的定位句（本轮修订）

## 版本 A（稳）
NeoDev 把需求、上下文、执行与验收连接成一条可追踪的人机协作研发链路。

## 版本 B（更产品化）
NeoDev 不是另一个任务工具，而是 AI 时代研发协作的闭环执行层。

## 版本 C（更有画面）
NeoDev 让团队不再靠转述推进研发，而是靠共享上下文与可审查结果推进研发。

### 当前判断
- 若用于内部战略讨论：A 最稳
- 若用于对外定位探索：C 最有记忆点
- 若用于产品叙事中段：B 比较适合

---

# 10. 反思（反思阶段）

本轮迭代后，我对研究过程本身也做一个简短反思。

## 10.1 这轮做对了什么
- 没停在功能列表，而是抽象到了“默认工作流定义权”
- 补了第二轮调研，把方法论叙事和 adoption 证据连了起来
- 显式做了自审，避免一次性输出过早收口

## 10.2 这轮仍然不够的地方
- 仍以官方材料为主，真实用户社区反馈占比不够
- 对 GitHub / Jira 的组织层 adoption 细节，还可以再补行业案例
- 对 Figma Dev Mode 的真实开发者口碑与争议，还值得单独做一轮
- 对中国团队环境下，这些心智是否会因飞书/企业微信/本地协作习惯而偏移，还未覆盖

## 10.3 如果继续下一轮，最值得补的方向
1. 补用户访谈/社区讨论/案例文章，验证这些心智是否真被用户内化
2. 单独研究 AI 工具如何改变“研发负责人/PM/Tech Lead”的角色
3. 补“为什么很多团队有 Notion 但执行还回到 Jira/GitHub”的断层机制
4. 补中国本土团队工作流与这些国际产品心智之间的偏差

---

# 11. 最终结论

如果只用一句话概括这轮研究：

**现代研发工具的竞争，不只是效率竞争，而是“谁来定义用户默认工作流”的竞争。**

而对 NeoDev 来说，最值得占据的位置不是“更智能”，而是：

**在 AI 已经进入研发流程的前提下，把需求、上下文、执行、证据、验收重新连接成一条可追踪、可协同、可审查、可验收的闭环链路。**

这比做一个更强的生成器、更快的任务板、或更聪明的文档工具，都更有可能形成长期心智位。

---

# 参考资料（本轮查阅）

## GitHub
- GitHub Issues / Projects: https://github.com/features/issues

## Linear
- Linear Method: https://linear.app/method
- Principles & Practices: https://linear.app/method/introduction
- Write issues not user stories: https://linear.app/method/write-issues-not-user-stories
- Generate momentum: https://linear.app/method/building-with-momentum
- Scope projects down: https://linear.app/method/scope-projects

## Notion
- Notion Product: https://www.notion.com/product
- Notion Projects: https://www.notion.com/product/projects
- Notion × OpenAI customer story: https://www.notion.com/customers/openai

## Figma
- Figma multiplayer technology: https://www.figma.com/blog/how-figmas-multiplayer-technology-works/
- Figma Dev Mode: https://www.figma.com/blog/introducing-dev-mode/

## Cursor
- Cursor homepage: https://cursor.com
- Cursor agent best practices: https://cursor.com/blog/agent-best-practices
- Cursor × Salesforce: https://cursor.com/blog/salesforce
- Cursor research / self-driving codebases: https://cursor.com/blog/self-driving-codebases

## Vercel
- Vercel environments / preview deployments: https://vercel.com/docs/deployments/environments
- Vercel comments overview: https://vercel.com/docs/comments
- Vercel customers / case studies: https://vercel.com/customers

## Jira
- Jira features: https://www.atlassian.com/software/jira/features
