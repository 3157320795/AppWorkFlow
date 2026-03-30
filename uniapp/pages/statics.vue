<template>
  <view class="container">
    <view class="header">
      <text class="title">STATICS</text>
    </view>
    <view class="content">
      <text class="product">产品: 猪猪来财</text>
      <text class="scheme">方案: 标准实用型</text>
      <text class="hint">页面开发中...</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      productName: "猪猪来财",
      pageName: "statics"
    };
  },
  onLoad() {
    console.log("页面加载:", this.pageName);
  }
};
</script>

<style>
.container {
  padding: 20px;
}
.header {
  margin-bottom: 20px;
}
.title {
  font-size: 24px;
  font-weight: bold;
}
.content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.product, .scheme, .hint {
  font-size: 14px;
  color: #666;
}
</style>
