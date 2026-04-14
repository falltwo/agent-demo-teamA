<script setup lang="ts">
import * as echarts from "echarts";
import type { ECharts, EChartsCoreOption } from "echarts";
import { nextTick, onMounted, onUnmounted, ref } from "vue";

const props = defineProps<{
  option: Record<string, unknown>;
}>();

const hostRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

function applyOption(inst: ECharts) {
  inst.setOption(props.option as EChartsCoreOption, {
    notMerge: true,
    lazyUpdate: true,
  });
}

onMounted(() => {
  nextTick(() => {
    requestAnimationFrame(() => {
      const el = hostRef.value;
      if (!el) {
        return;
      }
      chart = echarts.init(el, undefined, { renderer: "canvas" });
      requestAnimationFrame(() => {
        if (chart) {
          applyOption(chart);
        }
      });
      resizeObserver = new ResizeObserver(() => {
        chart?.resize();
      });
      resizeObserver.observe(el);
    });
  });
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="hostRef" class="chart-host" role="img" aria-label="圖表" />
</template>

<style scoped>
.chart-host {
  width: 100%;
  height: 400px;
  min-height: 240px;
}
</style>
