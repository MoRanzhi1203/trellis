window.TRELLIS = {
  meta: {
    name: "Trellis",
    planDays: 12,
    startDate: "2026-11-05",
    reviewOffsets: [1, 2, 4, 7, 15],
    updatedAt: "2026-11-05"
  },
  days: [
    {
      day: 1,
      date: "2026-11-05",
      learned: true,
      note: "第一天 · 已学习，进入复习周期",
      groups: [
        {
          key: "work",
          label: "work 家族 · 工作与产出",
          words: [
            { id: "d1-01", term: "work", kind: "word", main: true, senses: [{ pos: "n.", meanings: ["工作(量)", "职业", "产品", "著作", "工作地点"] }] },
            { id: "d1-02", term: "work against", kind: "phrase", senses: [{ pos: "", meanings: ["竭力反对", "妨碍"] }] },
            { id: "d1-03", term: "work on", kind: "phrase", senses: [{ pos: "", meanings: ["从事于，致力于"] }] },
            { id: "d1-04", term: "work out", kind: "phrase", senses: [{ pos: "", meanings: ["成功地发展", "找到(解决办法等)", "计算出"] }] },
            { id: "d1-05", term: "workout", kind: "word", senses: [{ pos: "n.", meanings: ["锻炼"] }] },
            { id: "d1-06", term: "workplace", kind: "word", senses: [{ pos: "n.", meanings: ["工作场所"] }] },
            { id: "d1-07", term: "workaholic", kind: "word", senses: [{ pos: "n.", meanings: ["工作狂"] }] },
            { id: "d1-08", term: "workstation", kind: "word", senses: [{ pos: "n.", meanings: ["工作台"] }] },
            { id: "d1-09", term: "patchwork", kind: "word", senses: [{ pos: "n.", meanings: ["拼凑物", "混杂物"] }] }
          ]
        },
        {
          key: "career",
          label: "职业与劳动",
          words: [
            { id: "d1-10", term: "career", kind: "word", senses: [{ pos: "n.", meanings: ["生涯", "经历", "职业"] }] },
            { id: "d1-11", term: "labo(u)r", kind: "word", senses: [{ pos: "n.", meanings: ["劳动", "努力", "劳动力", "[L-](英国)工党"] }, { pos: "v.", meanings: ["劳动，工作", "艰苦地做，吃力地做"] }] }
          ]
        },
        {
          key: "stat",
          label: "stat 家族 · 站立 → 状态 / 国家",
          words: [
            { id: "d1-12", term: "state", kind: "word", main: true, senses: [{ pos: "n.", meanings: ["州", "国家", "政府", "状态，情况"] }, { pos: "v.", meanings: ["声明", "规定"] }, { pos: "adj.", meanings: ["州的", "国家的", "国有的"] }] },
            { id: "d1-13", term: "stated", kind: "word", senses: [{ pos: "adj.", meanings: ["规定的", "声明的"] }] },
            { id: "d1-14", term: "statement", kind: "word", senses: [{ pos: "n.", meanings: ["声明", "表述"] }] },
            { id: "d1-15", term: "overstate", kind: "word", senses: [{ pos: "v.", meanings: ["过分夸大"] }] },
            { id: "d1-16", term: "status", kind: "word", senses: [{ pos: "n.", meanings: ["地位", "身份", "情形，状况", "重要性"] }] },
            { id: "d1-17", term: "statute", kind: "word", senses: [{ pos: "n.", meanings: ["成文法", "法令，法规"] }] },
            { id: "d1-18", term: "estate", kind: "word", senses: [{ pos: "n.", meanings: ["地产", "庄园", "住宅区", "遗产"] }] },
            { id: "d1-19", term: "statistical", kind: "word", senses: [{ pos: "adj.", meanings: ["统计的", "统计学的"] }] }
          ]
        }
      ],
      graph: {
        roots: [
          { id: "g-work", label: "work", gloss: "工作 / 运转", fam: "work" },
          { id: "g-stat", label: "stat", gloss: "站立 → 状态 / 国家", fam: "stat" },
          { id: "g-labor", label: "labor", gloss: "劳动", fam: "labor" }
        ],
        branches: [
          { id: "b-work-core", root: "g-work", label: "核心 · 工作" },
          { id: "b-work-phrase", root: "g-work", label: "短语 · 动作" },
          { id: "b-work-compound", root: "g-work", label: "合成 · 人与物" },
          { id: "b-stat-state", root: "g-stat", label: "状态 · 身份" },
          { id: "b-stat-say", root: "g-stat", label: "陈述 · 声明" },
          { id: "b-stat-law", root: "g-stat", label: "法规 · 财产" },
          { id: "b-stat-data", root: "g-stat", label: "统计" },
          { id: "b-labor-work", root: "g-labor", label: "劳动" },
          { id: "b-labor-career", root: "g-labor", label: "生涯" }
        ],
        links: [
          { from: "g-work", to: "b-work-core" },
          { from: "g-work", to: "b-work-phrase" },
          { from: "g-work", to: "b-work-compound" },
          { from: "b-work-core", to: "d1-01" },
          { from: "b-work-phrase", to: "d1-02", rel: "against" },
          { from: "b-work-phrase", to: "d1-03", rel: "on" },
          { from: "b-work-phrase", to: "d1-04", rel: "out" },
          { from: "b-work-compound", to: "d1-05", rel: "work+out" },
          { from: "b-work-compound", to: "d1-06", rel: "work+place" },
          { from: "b-work-compound", to: "d1-07", rel: "work+aholic" },
          { from: "b-work-compound", to: "d1-08", rel: "work+station" },
          { from: "b-work-compound", to: "d1-09", rel: "patch+work" },
          { from: "g-stat", to: "b-stat-state" },
          { from: "g-stat", to: "b-stat-say" },
          { from: "g-stat", to: "b-stat-law" },
          { from: "g-stat", to: "b-stat-data" },
          { from: "b-stat-state", to: "d1-12" },
          { from: "b-stat-state", to: "d1-16", rel: "status" },
          { from: "b-stat-say", to: "d1-13", rel: "-ed" },
          { from: "b-stat-say", to: "d1-14", rel: "-ment" },
          { from: "b-stat-say", to: "d1-15", rel: "over-" },
          { from: "b-stat-law", to: "d1-17", rel: "statute" },
          { from: "b-stat-law", to: "d1-18", rel: "estate" },
          { from: "b-stat-data", to: "d1-19", rel: "-al" },
          { from: "g-labor", to: "b-labor-work" },
          { from: "g-labor", to: "b-labor-career", dash: true },
          { from: "b-labor-work", to: "d1-11" },
          { from: "b-labor-career", to: "d1-10", dash: true }
        ]
      }
    }
  ]
};
