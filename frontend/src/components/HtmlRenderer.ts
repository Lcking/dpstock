import { defineComponent, h } from 'vue';

export default defineComponent({
  name: 'HtmlRenderer',
  props: {
    html: {
      type: String,
      required: false
    }
  },
  render() {
    return h('div', {
      class: 'analysis-html',
      innerHTML: this.html || '--'
    });
  }
});
