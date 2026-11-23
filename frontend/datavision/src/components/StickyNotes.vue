<script setup>
import { ref } from 'vue'

// 两张独立的粘滞说明卡：分别对应「历史特殊记录」与「小项命名泛化」
const openSpecial = ref(true)
const openGeneric = ref(true)
</script>

<template>
  <div class="sticky-notes">
    <section class="note-card" :class="{ 'is-collapsed': !openSpecial }">
      <button type="button" class="note-head" @click="openSpecial = !openSpecial">
        <span class="note-dot"></span>
        <span class="note-heading">
          <strong>历史特殊记录的处理规则</strong>
          <small>1906 · 1956 双城 · 政体继承 · ROC/AIN/EOR</small>
        </span>
        <span class="note-toggle">{{ openSpecial ? '收起' : '展开' }}</span>
      </button>
      <div v-show="openSpecial" class="note-body">
        <p class="note-lead">这些记录不按常规口径一刀切，而是保留原值并打标记，避免历史被抹平。</p>
        <ul>
          <li><b>1906 届间奥运</b>：计入年度分布，但标记为非官方，默认排除在奖牌榜之外。</li>
          <li><b>1956 双城</b>：墨尔本与斯德哥尔摩原样保留，不合并城市；按届次聚合分析。</li>
          <li><b>政体变迁</b>：URS→EUN→RUS→ROC→AIN、FRG/GDR→GER、YUG→SCG→SRB 映射到继承实体，仅用于长周期曲线。</li>
          <li><b>ROC / AIN / EOR</b>：ROC 与 AIN 并入俄罗斯继承链；EOR 难民代表团独立保留，不并入任何国家。</li>
          <li><b>抵制潮 1980 / 1984</b>：不做特殊修补，参赛国数量的骤降本身就是分析对象。</li>
        </ul>
      </div>
    </section>

    <section class="note-card" :class="{ 'is-collapsed': !openGeneric }">
      <button type="button" class="note-head" @click="openGeneric = !openGeneric">
        <span class="note-dot is-gold"></span>
        <span class="note-heading">
          <strong>2020 年起小项命名泛化</strong>
          <small>近两届 21.62% 记录无法还原具体小项</small>
        </span>
        <span class="note-toggle">{{ openGeneric ? '收起' : '展开' }}</span>
      </button>
      <div v-show="openGeneric" class="note-body">
        <p class="note-lead">2020 / 2024 两届出现 Men、Women、Men Team、Relay Only Athlete 等泛化写法。</p>
        <ul>
          <li><b>处理策略</b>：保留原始记录，不删除、不改写，新增泛化标记字段。</li>
          <li><b>统计降维</b>：涉及小项数量的指标，在这两届自动降维到「运动大类 × 性别」粒度。</li>
          <li><b>展示规则</b>：泛化届次的小项曲线不与其前届直接比较，图表与结论处均加注说明。</li>
          <li><b>为什么不剔除</b>：剔除会系统性丢掉近两届 21.62% 的记录，且只影响最新数据，偏差更大。</li>
        </ul>
      </div>
    </section>
  </div>
</template>
