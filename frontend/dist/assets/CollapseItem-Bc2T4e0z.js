import{d as S,A as i,H as j,I as u,J as x,K as $,L as l,M as H,O,P as T,r as V,Q as N,R as K,S as _,T as F,U as q,V as Z,W as J,X as P,Y as Q,Z as X,$ as Y,a0 as k,a1 as G,a2 as A,a3 as ee,a4 as re,a5 as te,a6 as ae,a7 as oe,a8 as le,a9 as se,aa as D}from"./index-Dst_PqRe.js";const ie=S({name:"ChevronLeft",render(){return i("svg",{viewBox:"0 0 16 16",fill:"none",xmlns:"http://www.w3.org/2000/svg"},i("path",{d:"M10.3536 3.14645C10.5488 3.34171 10.5488 3.65829 10.3536 3.85355L6.20711 8L10.3536 12.1464C10.5488 12.3417 10.5488 12.6583 10.3536 12.8536C10.1583 13.0488 9.84171 13.0488 9.64645 12.8536L5.14645 8.35355C4.95118 8.15829 4.95118 7.84171 5.14645 7.64645L9.64645 3.14645C9.84171 2.95118 10.1583 2.95118 10.3536 3.14645Z",fill:"currentColor"}))}});function ne(e){const{fontWeight:n,textColor1:s,textColor2:a,textColorDisabled:d,dividerColor:r,fontSize:c}=e;return{titleFontSize:c,titleFontWeight:n,dividerColor:r,titleTextColor:s,titleTextColorDisabled:d,fontSize:c,textColor:a,arrowColor:a,arrowColorDisabled:d,itemMargin:"16px 0 0 0",titlePadding:"16px 0 0 0"}}const de={common:j,self:ne},ce=u("collapse","width: 100%;",[u("collapse-item",`
 font-size: var(--n-font-size);
 color: var(--n-text-color);
 transition:
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 margin: var(--n-item-margin);
 `,[x("disabled",[l("header","cursor: not-allowed;",[l("header-main",`
 color: var(--n-title-text-color-disabled);
 `),u("collapse-item-arrow",`
 color: var(--n-arrow-color-disabled);
 `)])]),u("collapse-item","margin-left: 32px;"),$("&:first-child","margin-top: 0;"),$("&:first-child >",[l("header","padding-top: 0;")]),x("left-arrow-placement",[l("header",[u("collapse-item-arrow","margin-right: 4px;")])]),x("right-arrow-placement",[l("header",[u("collapse-item-arrow","margin-left: 4px;")])]),l("content-wrapper",[l("content-inner","padding-top: 16px;"),O({duration:"0.15s"})]),x("active",[l("header",[x("active",[u("collapse-item-arrow","transform: rotate(90deg);")])])]),$("&:not(:first-child)","border-top: 1px solid var(--n-divider-color);"),H("disabled",[x("trigger-area-main",[l("header",[l("header-main","cursor: pointer;"),u("collapse-item-arrow","cursor: default;")])]),x("trigger-area-arrow",[l("header",[u("collapse-item-arrow","cursor: pointer;")])]),x("trigger-area-extra",[l("header",[l("header-extra","cursor: pointer;")])])]),l("header",`
 font-size: var(--n-title-font-size);
 display: flex;
 flex-wrap: nowrap;
 align-items: center;
 transition: color .3s var(--n-bezier);
 position: relative;
 padding: var(--n-title-padding);
 color: var(--n-title-text-color);
 `,[l("header-main",`
 display: flex;
 flex-wrap: nowrap;
 align-items: center;
 font-weight: var(--n-title-font-weight);
 transition: color .3s var(--n-bezier);
 flex: 1;
 color: var(--n-title-text-color);
 `),l("header-extra",`
 display: flex;
 align-items: center;
 transition: color .3s var(--n-bezier);
 color: var(--n-text-color);
 `),u("collapse-item-arrow",`
 display: flex;
 transition:
 transform .15s var(--n-bezier),
 color .3s var(--n-bezier);
 font-size: 18px;
 color: var(--n-arrow-color);
 `)])])]),pe=Object.assign(Object.assign({},_.props),{defaultExpandedNames:{type:[Array,String],default:null},expandedNames:[Array,String],arrowPlacement:{type:String,default:"left"},accordion:{type:Boolean,default:!1},displayDirective:{type:String,default:"if"},triggerAreas:{type:Array,default:()=>["main","extra","arrow"]},onItemHeaderClick:[Function,Array],"onUpdate:expandedNames":[Function,Array],onUpdateExpandedNames:[Function,Array],onExpandedNamesChange:{type:[Function,Array],validator:()=>!0,default:void 0}}),L=Z("n-collapse"),he=S({name:"Collapse",props:pe,slots:Object,setup(e,{slots:n}){const{mergedClsPrefixRef:s,inlineThemeDisabled:a,mergedRtlRef:d}=T(e),r=V(e.defaultExpandedNames),c=N(()=>e.expandedNames),v=K(c,r),C=_("Collapse","-collapse",ce,de,e,s);function p(m){const{"onUpdate:expandedNames":o,onUpdateExpandedNames:f,onExpandedNamesChange:y}=e;f&&P(f,m),o&&P(o,m),y&&P(y,m),r.value=m}function g(m){const{onItemHeaderClick:o}=e;o&&P(o,m)}function t(m,o,f){const{accordion:y}=e,{value:E}=v;if(y)m?(p([o]),g({name:o,expanded:!0,event:f})):(p([]),g({name:o,expanded:!1,event:f}));else if(!Array.isArray(E))p([o]),g({name:o,expanded:!0,event:f});else{const w=E.slice(),I=w.findIndex(z=>o===z);~I?(w.splice(I,1),p(w),g({name:o,expanded:!1,event:f})):(w.push(o),p(w),g({name:o,expanded:!0,event:f}))}}J(L,{props:e,mergedClsPrefixRef:s,expandedNamesRef:v,slots:n,toggleItem:t});const h=F("Collapse",d,s),R=N(()=>{const{common:{cubicBezierEaseInOut:m},self:{titleFontWeight:o,dividerColor:f,titlePadding:y,titleTextColor:E,titleTextColorDisabled:w,textColor:I,arrowColor:z,fontSize:M,titleFontSize:U,arrowColorDisabled:B,itemMargin:W}}=C.value;return{"--n-font-size":M,"--n-bezier":m,"--n-text-color":I,"--n-divider-color":f,"--n-title-padding":y,"--n-title-font-size":U,"--n-title-text-color":E,"--n-title-text-color-disabled":w,"--n-title-font-weight":o,"--n-arrow-color":z,"--n-arrow-color-disabled":B,"--n-item-margin":W}}),b=a?q("collapse",void 0,R,e):void 0;return{rtlEnabled:h,mergedTheme:C,mergedClsPrefix:s,cssVars:a?void 0:R,themeClass:b==null?void 0:b.themeClass,onRender:b==null?void 0:b.onRender}},render(){var e;return(e=this.onRender)===null||e===void 0||e.call(this),i("div",{class:[`${this.mergedClsPrefix}-collapse`,this.rtlEnabled&&`${this.mergedClsPrefix}-collapse--rtl`,this.themeClass],style:this.cssVars},this.$slots)}}),me=S({name:"CollapseItemContent",props:{displayDirective:{type:String,required:!0},show:Boolean,clsPrefix:{type:String,required:!0}},setup(e){return{onceTrue:Y(k(e,"show"))}},render(){return i(Q,null,{default:()=>{const{show:e,displayDirective:n,onceTrue:s,clsPrefix:a}=this,d=n==="show"&&s,r=i("div",{class:`${a}-collapse-item__content-wrapper`},i("div",{class:`${a}-collapse-item__content-inner`},this.$slots));return d?X(r,[[G,e]]):e?r:null}})}}),fe={title:String,name:[String,Number],disabled:Boolean,displayDirective:String},ge=S({name:"CollapseItem",props:fe,setup(e){const{mergedRtlRef:n}=T(e),s=ae(),a=oe(()=>{var t;return(t=e.name)!==null&&t!==void 0?t:s}),d=se(L);d||le("collapse-item","`n-collapse-item` must be placed inside `n-collapse`.");const{expandedNamesRef:r,props:c,mergedClsPrefixRef:v,slots:C}=d,p=N(()=>{const{value:t}=r;if(Array.isArray(t)){const{value:h}=a;return!~t.findIndex(R=>R===h)}else if(t){const{value:h}=a;return h!==t}return!0});return{rtlEnabled:F("Collapse",n,v),collapseSlots:C,randomName:s,mergedClsPrefix:v,collapsed:p,triggerAreas:k(c,"triggerAreas"),mergedDisplayDirective:N(()=>{const{displayDirective:t}=e;return t||c.displayDirective}),arrowPlacement:N(()=>c.arrowPlacement),handleClick(t){let h="main";D(t,"arrow")&&(h="arrow"),D(t,"extra")&&(h="extra"),c.triggerAreas.includes(h)&&d&&!e.disabled&&d.toggleItem(p.value,a.value,t)}}},render(){const{collapseSlots:e,$slots:n,arrowPlacement:s,collapsed:a,mergedDisplayDirective:d,mergedClsPrefix:r,disabled:c,triggerAreas:v}=this,C=A(n.header,{collapsed:a},()=>[this.title]),p=n["header-extra"]||e["header-extra"],g=n.arrow||e.arrow;return i("div",{class:[`${r}-collapse-item`,`${r}-collapse-item--${s}-arrow-placement`,c&&`${r}-collapse-item--disabled`,!a&&`${r}-collapse-item--active`,v.map(t=>`${r}-collapse-item--trigger-area-${t}`)]},i("div",{class:[`${r}-collapse-item__header`,!a&&`${r}-collapse-item__header--active`]},i("div",{class:`${r}-collapse-item__header-main`,onClick:this.handleClick},s==="right"&&C,i("div",{class:`${r}-collapse-item-arrow`,key:this.rtlEnabled?0:1,"data-arrow":!0},A(g,{collapsed:a},()=>[i(ee,{clsPrefix:r},{default:()=>this.rtlEnabled?i(ie,null):i(re,null)})])),s==="left"&&C),te(p,{collapsed:a},t=>i("div",{class:`${r}-collapse-item__header-extra`,onClick:this.handleClick,"data-extra":!0},t))),i(me,{clsPrefix:r,displayDirective:d,show:!a},n))}});export{he as N,ge as a};
