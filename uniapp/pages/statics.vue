<template>
  <view class="statics-page bg-surface text-on-surface min-h-screen pb-32">
    <!-- Top App Bar -->
    <header class="bg-surface sticky top-0 z-40">
      <view class="flex items-center justify-between px-6 py-4">
        <view class="flex items-center gap-3">
          <text class="iconfont icon-account_balance_wallet text-primary text-40rpx"></text>
          <h1 class="font-headline font-bold text-36rpx tracking-tight text-on-surface">智能记账本</h1>
        </view>
        <view class="flex items-center gap-4">
          <button class="p-2 rounded-full active:scale-95 duration-200" @click="handleSearch">
            <text class="iconfont icon-search text-36rpx"></text>
          </button>
          <button class="p-2 rounded-full active:scale-95 duration-200" @click="handleMore">
            <text class="iconfont icon-more_vert text-36rpx"></text>
          </button>
        </view>
      </view>
      <view class="bg-surface-container-low h-1px w-full"></view>
    </header>

    <main class="px-6 pt-8 space-y-8">
      <!-- Time Picker Shell -->
      <section class="flex flex-col gap-6">
        <view class="flex items-center justify-between">
          <h2 class="font-headline font-bold text-48rpx tracking-tight">统计分析</h2>
          <view class="bg-surface-container-low p-1 rounded-xl flex items-center gap-1">
            <button 
              v-for="(item, index) in timePeriods" 
              :key="index"
              :class="[
                'px-4 py-1.5 rounded-lg text-sm font-medium transition-colors',
                currentPeriod === index ? 'bg-surface-container-lowest text-primary shadow-sm' : 'text-on-surface-variant hover:bg-surface-container-high'
              ]"
              @click="switchPeriod(index)"
            >
              {{ item }}
            </button>
          </view>
        </view>
        <view class="flex items-center justify-center gap-4 text-on-surface-variant">
          <button class="iconfont icon-chevron_left text-36rpx active:scale-90 transition-transform" @click="prevPeriod"></button>
          <span class="font-semibold text-on-surface text-28rpx">{{ currentDateRange }}</span>
          <button class="iconfont icon-chevron_right text-36rpx active:scale-90 transition-transform" @click="nextPeriod"></button>
        </view>
      </section>

      <!-- Trend Chart Section -->
      <section class="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
        <view class="flex justify-between items-end mb-8">
          <view>
            <p class="text-24rpx text-on-surface-variant mb-1">总支出 (本周)</p>
            <h3 class="font-headline font-extrabold text-64rpx text-tertiary">¥{{ totalExpense }}</h3>
          </view>
          <view class="text-right">
            <p class="text-24rpx text-on-surface-variant mb-1">总收入</p>
            <p class="font-headline font-bold text-36rpx text-secondary">¥{{ totalIncome }}</p>
          </view>
        </view>
        <!-- Trend Chart -->
        <view class="h-192rpx w-full relative overflow-hidden flex items-end gap-2 px-2">
          <svg class="absolute inset-0 w-full h-full" preserveAspectRatio="none" viewBox="0 0 400 100">
            <path d="M0,80 Q50,75 100,40 T200,50 T300,20 T400,30" fill="none" stroke="#005bbf" stroke-linecap="round" stroke-width="3"></path>
            <path d="M0,80 Q50,75 100,40 T200,50 T300,20 T400,30 L400,100 L0,100 Z" fill="url(#grad1)"></path>
            <defs>
              <linearGradient id="grad1" x1="0%" x2="0%" y1="0%" y2="100%">
                <stop offset="0%" style="stop-color:rgba(0, 91, 191, 0.15);stop-opacity:1"></stop>
                <stop offset="100%" style="stop-color:rgba(0, 91, 191, 0);stop-opacity:1"></stop>
              </linearGradient>
            </defs>
          </svg>
          <!-- X-axis Labels -->
          <view class="absolute bottom-0 w-full flex justify-between text-20rpx text-on-surface-variant font-medium px-1">
            <span>周一</span>
            <span>周二</span>
            <span>周三</span>
            <span>周四</span>
            <span>周五</span>
            <span>周六</span>
            <span>周日</span>
          </view>
        </view>
      </section>

      <!-- Category Breakdown Grid -->
      <view class="grid gap-8">
        <!-- Pie Chart Section -->
        <section class="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
          <view class="flex items-center justify-between mb-8">
            <h4 class="font-bold text-32rpx">分类占比</h4>
            <view class="bg-surface-container-low rounded-lg p-0.5 flex">
              <button 
                :class="[
                  'px-3 py-1 rounded-md text-xs font-bold shadow-sm',
                  currentCategoryType === 'expense' ? 'bg-surface-container-lowest text-primary' : 'text-on-surface-variant font-medium'
                ]"
                @click="switchCategoryType('expense')"
              >
                支出
              </button>
              <button 
                :class="[
                  'px-3 py-1 rounded-md text-xs font-medium',
                  currentCategoryType === 'income' ? 'bg-surface-container-lowest text-primary' : 'text-on-surface-variant'
                ]"
                @click="switchCategoryType('income')"
              >
                收入
              </button>
            </view>
          </view>
          <view class="flex items-center gap-8">
            <!-- Donut Chart -->
            <view class="relative w-128rpx h-128rpx flex-shrink-0">
              <svg class="w-full h-full" viewBox="0 0 36 36">
                <circle class="stroke-surface-container-high" cx="18" cy="18" fill="none" r="16" stroke-width="4"></circle>
                <circle class="stroke-primary" cx="18" cy="18" fill="none" r="16" stroke-dasharray="45, 100" stroke-dashoffset="25" stroke-linecap="round" stroke-width="4"></circle>
                <circle class="stroke-tertiary" cx="18" cy="18" fill="none" r="16" stroke-dasharray="20, 100" stroke-dashoffset="80" stroke-linecap="round" stroke-width="4"></circle>
                <circle class="stroke-secondary" cx="18" cy="18" fill="none" r="16" stroke-dasharray="15, 100" stroke-dashoffset="100" stroke-linecap="round" stroke-width="4"></circle>
              </svg>
              <view class="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span class="text-20rpx text-on-surface-variant font-medium uppercase tracking-wider">总计</span>
                <span class="font-bold text-24rpx">100%</span>
              </view>
            </view>
            <!-- Legend -->
            <view class="flex-grow space-y-3">
              <view class="flex items-center justify-between" v-for="(item, index) in categoryData" :key="index">
                <view class="flex items-center gap-2">
                  <view :class="['w-10rpx h-10rpx rounded-full', item.colorClass]"></view>
                  <span class="text-28rpx font-medium">{{ item.name }}</span>
                </view>
                <span class="text-28rpx font-bold">{{ item.percentage }}%</span>
              </view>
            </view>
          </view>
        </section>

        <!-- Category List Section -->
        <section class="space-y-4">
          <view 
            class="bg-surface-container-lowest rounded-xl p-4 flex items-center justify-between hover:translate-x-1 transition-transform cursor-pointer" 
            v-for="(item, index) in categoryList" 
            :key="index"
            @click="viewCategoryDetail(item)"
          >
            <view class="flex items-center gap-4">
              <view :class="['w-4rpx h-32rpx rounded-full', item.colorClass]"></view>
              <view :class="['w-80rpx h-80rpx rounded-full flex items-center justify-center', item.bgColorClass]">
                <text :class="['iconfont text-36rpx', item.iconClass]"></text>
              </view>
              <view>
                <p class="font-bold text-on-surface text-28rpx">{{ item.name }}</p>
                <p class="text-22rpx text-on-surface-variant">{{ item.transactionCount }} 笔交易</p>
              </view>
            </view>
            <p class="font-headline font-bold text-28rpx">¥{{ item.amount }}</p>
          </view>
        </section>
      </view>

      <!-- Yearly Summary Bar Chart -->
      <section class="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
        <view class="flex items-center justify-between mb-6">
          <h4 class="font-bold text-32rpx">年度收支趋势</h4>
          <view class="flex gap-4">
            <view class="flex items-center gap-1.5">
              <view class="w-8rpx h-8rpx rounded-full bg-primary/40"></view>
              <span class="text-20rpx text-on-surface-variant font-medium">收入</span>
            </view>
            <view class="flex items-center gap-1.5">
              <view class="w-8rpx h-8rpx rounded-full bg-primary"></view>
              <span class="text-20rpx text-on-surface-variant font-medium">结余</span>
            </view>
          </view>
        </view>
        <view class="h-128rpx flex items-end justify-between gap-1 px-2">
          <!-- Month Bars -->
          <view class="group relative flex flex-col items-center flex-1 gap-1" v-for="(month, index) in yearlyData" :key="index">
            <view :class="['w-full rounded-t-sm transition-all', month.incomeClass]" :style="{ height: month.incomeHeight + '%' }"></view>
            <view 
              :class="[
                'w-full bg-primary rounded-t-sm transition-all -mt-8rpx',
                month.current ? 'ring-2 ring-primary ring-offset-2' : 'group-hover:bg-primary-container'
              ]" 
              :style="{ height: month.balanceHeight + '%' }"
              v-if="month.balanceHeight > 0"
            ></view>
            <span :class="['text-16rpx font-medium mt-8rpx', month.current ? 'text-primary font-bold' : 'text-on-surface-variant']">{{ index + 1 }}月</span>
          </view>
        </view>
      </section>
    </main>

    <!-- Floating Action Button -->
    <view class="fixed bottom-48rpx right-24rpx md:hidden z-50">
      <button class="w-112rpx h-112rpx bg-primary text-white rounded-2xl shadow-lg flex items-center justify-center active:scale-90 transition-transform" @click="handleAdd">
        <text class="iconfont icon-add text-56rpx"></text>
      </button>
    </view>

    <!-- Bottom Navigation Bar -->
    <nav class="fixed bottom-0 left-0 w-full flex justify-around items-center px-4 pb-24rpx pt-8rpx bg-white/80 backdrop-blur-xl border-t border-surface-container-low shadow-sm z-50 rounded-t-2xl">
      <view class="flex flex-col items-center justify-center text-on-surface-variant px-4 py-2 hover:text-primary active:scale-90 transition-transform" @click="navigateTo('/pages/index/index')">
        <text class="iconfont icon-home text-36rpx"></text>
        <span class="font-body text-20rpx font-medium mt-4rpx">首页</span>
      </view>
      <view class="flex flex-col items-center justify-center text-on-surface-variant px-4 py-2 hover:text-primary active:scale-90 transition-transform" @click="navigateTo('/pages/bill/bill')">
        <text class="iconfont icon-receipt_long text-36rpx"></text>
        <span class="font-body text-20rpx font-medium mt-4rpx">账单</span>
      </view>
      <view class="flex flex-col items-center justify-center text-primary bg-primary/10 rounded-xl px-4 py-2 active:scale-90 transition-transform">
        <text class="iconfont icon-leaderboard text-36rpx" style="font-variation-settings: 'FILL' 1;"></text>
        <span class="font-body text-20rpx font-medium mt-4rpx">统计</span>
      </view>
      <view class="flex flex-col items-center justify-center text-on-surface-variant px-4 py-2 hover:text-primary active:scale-90 transition-transform" @click="navigateTo('/pages/mine/mine')">
        <text class="iconfont icon-person text-36rpx"></text>
        <span class="font-body text-20rpx font-medium mt-4rpx">我的</span>
      </view>
    </nav>
  </view>
</template>

<script>
export default {
  data() {
    return {
      timePeriods: ['周', '月', '季', '年'],
      currentPeriod: 0,
      currentDateRange: '2023年 10月30日 - 11月05日',
      totalExpense: '3,482.00',
      totalIncome: '12,500.00',
      currentCategoryType: 'expense',
      categoryData: [
        { name: '餐饮', percentage: 45, colorClass: 'bg-primary' },
        { name: '交通', percentage: 20, colorClass: 'bg-tertiary' },
        { name: '购物', percentage: 15, colorClass: 'bg-secondary' }
      ],
      categoryList: [
        { 
          name: '餐饮美食', 
          transactionCount: 12, 
          amount: '1,566.90', 
          colorClass: 'bg-primary', 
          bgColorClass: 'bg-primary/10', 
          iconClass: 'icon-restaurant text-primary' 
        },
        { 
          name: '交通出行', 
          transactionCount: 8, 
          amount: '696.40', 
          colorClass: 'bg-tertiary', 
          bgColorClass: 'bg-tertiary/10', 
          iconClass: 'icon-directions_car text-tertiary' 
        },
        { 
          name: '休闲购物', 
          transactionCount: 4, 
          amount: '522.30', 
          colorClass: 'bg-secondary', 
          bgColorClass: 'bg-secondary/10', 
          iconClass: 'icon-shopping_bag text-secondary' 
        }
      ],
      yearlyData: [
        { incomeHeight: 40, balanceHeight: 30, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 60, balanceHeight: 45, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 55, balanceHeight: 20, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 80, balanceHeight: 65, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 70, balanceHeight: 50, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 90, balanceHeight: 75, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 85, balanceHeight: 70, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 40, balanceHeight: 25, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 65, balanceHeight: 40, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 75, balanceHeight: 60, incomeClass: 'bg-primary/10', current: false },
        { incomeHeight: 85, balanceHeight: 70, incomeClass: 'bg-primary/20', current: true },
        { incomeHeight: 20, balanceHeight: 0, incomeClass: 'bg-surface-container-high opacity-40', current: false }
      ]
    }
  },
  methods: {
    switchPeriod(index) {
      this.currentPeriod = index
      // 这里可以根据不同的时间段更新日期范围和数据
    },
    prevPeriod() {
      // 上一个时间段逻辑
      uni.showToast({
        title: '上一个时间段',
        icon: 'none'
      })
    },
    nextPeriod() {
      // 下一个时间段逻辑
      uni.showToast({
        title: '下一个时间段',
        icon: 'none'
      })
    },
    switchCategoryType(type) {
      this.currentCategoryType = type
      // 这里可以切换支出/收入分类数据
    },
    viewCategoryDetail(item) {
      uni.showToast({
        title: `查看${item.name}详情`,
        icon: 'none'
      })
    },
    handleSearch() {
      uni.showToast({
        title: '搜索功能',
        icon: 'none'
      })
    },
    handleMore() {
      uni.showToast({
        title: '更多选项',
        icon: 'none'
      })
    },
    handleAdd() {
      uni.showToast({
        title: '添加记录',
        icon: 'none'
      })
    },
    navigateTo(url) {
      uni.switchTab({
        url
      })
    }
  }
}
</script>

<style scoped lang="scss">
@font-face {
  font-family: 'Material Icons';
  font-style: normal;
  font-weight: 400;
  src: url('https://fonts.googleapis.com/icon?family=Material+Icons') format('woff2');
}

.iconfont {
  font-family: 'Material Icons';
  font-weight: normal;
  font-style: normal;
  display: inline-block;
  line-height: 1;
  text-transform: none;
  letter-spacing: normal;
  word-wrap: normal;
  white-space: nowrap;
  direction: ltr;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  -moz-osx-font-smoothing: grayscale;
  font-feature-settings: 'liga';
}

/* 自定义图标 */
.icon-account_balance_wallet::before { content: '\e853'; }
.icon-search::before { content: '\e8b6'; }
.icon-more_vert::before { content: '\e5d4'; }
.icon-chevron_left::before { content: '\e314'; }
.icon-chevron_right::before { content: '\e315'; }
.icon-restaurant::before { content: '\e56c'; }
.icon-directions_car::before { content: '\e531'; }
.icon-shopping_bag::before { content: '\e1cc'; }
.icon-add::before { content: '\e145'; }
.icon-home::before { content: '\e88a'; }
.icon-receipt_long::before { content: '\e5c9'; }
.icon-leaderboard::before { content: '\e24a'; }
.icon-person::before { content: '\e7fd'; }

/* 颜色变量 */
$error: #ba1a1a;
$surface-container: #edeeef;
$outline-variant: #c1c6d6;
$on-secondary-fixed: #002108;
$secondary-container: #86f898;
$surface-bright: #f8f9fa;
$outline: #727785;
$primary: #005bbf;
$surface-tint: #005bc0;
$primary-fixed-dim: #adc7ff;
$secondary-fixed: #89fa9b;
$on-error-container: #93000a;
$surface-container-low: #f3f4f5;
$primary-fixed: #d8e2ff;
$on-tertiary-fixed-variant: #930004;
$on-surface: #191c1d;
$surface-container-highest: #e1e3e4;
$inverse-primary: #adc7ff;
$tertiary-fixed-dim: #ffb4a9;
$primary-container: #1a73e8;
$on-error: #ffffff;
$on-secondary: #ffffff;
$on-tertiary: #ffffff;
$surface-container-high: #e7e8e9;
$tertiary: #b81d17;
$tertiary-fixed: #ffdad5;
$on-tertiary-fixed: #410001;
$background: #f8f9fa;
$secondary: #006e2c;
$tertiary-container: #dc392c;
$secondary-fixed-dim: #6ddd81;
$inverse-surface: #2e3132;
$error-container: #ffdad6;
$on-secondary-fixed-variant: #005320;
$on-surface-variant: #414754;
$on-secondary-container: #00722f;
$surface: #f8f9fa;
$on-primary-fixed: #001a41;
$on-primary-container: #ffffff;
$on-background: #191c1d;
$on-primary: #ffffff;
$surface-dim: #d9dadb;
$on-tertiary-container: #ffffff;
$surface-container-lowest: #ffffff;
$inverse-on-surface: #f0f1f2;
$on-primary-fixed-variant: #004493;
$surface-variant: #e1e3e4;

/* 样式类 */
.statics-page {
  font-family: 'Inter', sans-serif;
  
  .font-headline {
    font-family: 'Manrope', sans-serif;
  }
  
  .bg-surface {
    background-color: $surface;
  }
  
  .bg-surface-container-low {
    background-color: $surface-container-low;
  }
  
  .bg-surface-container-lowest {
    background-color: $surface-container-lowest;
  }
  
  .bg-surface-container-high {
    background-color: $surface-container-high;
  }
  
  .bg-primary {
    background-color: $primary;
  }
  
  .bg-primary\/10 {
    background-color: rgba($primary, 0.1);
  }
  
  .bg-primary\/20 {
    background-color: rgba($primary, 0.2);
  }
  
  .bg-primary-container {
    background-color: $primary-container;
  }
  
  .bg-secondary {
    background-color: $secondary;
  }
  
  .bg-secondary\/10 {
    background-color: rgba($secondary, 0.1);
  }
  
  .bg-tertiary {
    background-color: $tertiary;
  }
  
  .bg-tertiary\/10 {
    background-color: rgba($tertiary, 0.1);
  }
  
  .text-on-surface {
    color: $on-surface;
  }
  
  .text-on-surface-variant {
    color: $on-surface-variant;
  }
  
  .text-primary {
    color: $primary;
  }
  
  .text-secondary {
    color: $secondary;
  }
  
  .text-tertiary {
    color: $tertiary;
  }
  
  .border-surface-container-low {
    border-color: $surface-container-low;
  }
  
  .shadow-sm {
    box-shadow: 0 4px 24px rgba(25, 28, 29, 0.04);
  }
  
  .h-1px {
    height: 1px;
  }
  
  .space-y-8 > * + * {
    margin-top: 32rpx;
  }
  
  .space-y-4 > * + * {
    margin-top: 16rpx;
  }
  
  .space-y-3 > * + * {
    margin-top: 12rpx;
  }
  
  .gap-1 > * + * {
    margin-left: 4rpx;
  }
  
  .gap-2 > * + * {
    margin-left: 8rpx;
  }
  
  .gap-3 > * + * {
    margin-left: 12rpx;
  }
  
  .gap-4 > * + * {
    margin-left: 16rpx;
  }
  
  .gap-8 > * + * {
    margin-left: 32rpx;
  }
  
  .tracking-tight {
    letter-spacing: -0.02em;
  }
  
  .transition-transform {
    transition: transform 0.2s ease;
  }
  
  .transition-colors {
    transition: background-color 0.2s ease, color 0.2s ease;
  }
  
  .translate-x-1:hover {
    transform: translateX(4rpx);
  }
}
</style>