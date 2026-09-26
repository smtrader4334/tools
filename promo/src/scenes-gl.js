// WebGL 프래그먼트 셰이더 장면들 (훅 + 드롭 A 실사풍 배경)
let g = null;
let buf = null;
const progs = {};

const VS = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';

const LIB = `
precision highp float;
uniform vec2 R; uniform float T; uniform float U;
#define A (R.x/R.y)
float h21(vec2 p){vec3 p3=fract(vec3(p.xyx)*.1031);p3+=dot(p3,p3.yzx+33.33);return fract((p3.x+p3.y)*p3.z);}
float h11(float x){return h21(vec2(x,x*1.37+.1));}
float vn(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.-2.*f);
  return mix(mix(h21(i),h21(i+vec2(1,0)),u.x),mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),u.x),u.y);}
float fbm(vec2 p){float v=0.,a=.5;mat2 m=mat2(1.6,1.2,-1.2,1.6);for(int i=0;i<5;i++){v+=a*vn(p);p=m*p;a*=.5;}return v;}
float fbm3(vec2 p){float v=0.,a=.5;mat2 m=mat2(1.6,1.2,-1.2,1.6);for(int i=0;i<3;i++){v+=a*vn(p);p=m*p;a*=.5;}return v;}
vec2 UV(){vec2 uv=(gl_FragCoord.xy-.5*R)/R.y;return uv;}
vec3 tone(vec3 c){c=1.-exp(-c*1.1);return pow(c,vec3(1./1.1));}
float eio(float u){u=clamp(u,0.,1.);return u<.5?4.*u*u*u:1.-pow(-2.*u+2.,3.)/2.;}
vec2 vor(vec2 p){vec2 i=floor(p),f=fract(p);float d1=8.,d2=8.;
  for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){vec2 b=vec2(x,y);vec2 o=vec2(h21(i+b),h21(i+b+17.3));
    float d=length(b+o-f);if(d<d1){d2=d1;d1=d;}else if(d<d2)d2=d;}
  return vec2(d1,d2-d1);}
`;

const FS = {};

// ---------------------------------------------------------------- 훅: 천장 누수 → 대야
FS.hook = LIB + `
vec3 plaster(vec2 p, vec2 c){
  float n=fbm(p*3.);
  float fine=vn(p*90.)*.5+vn(p*170.)*.5;
  vec3 base=vec3(.86,.84,.79)*(0.9+0.12*n)-fine*.035;
  // 물 얼룩: 번진 테두리(티드라인) 여러 겹
  float d=length((p-c)*vec2(1.,1.25))+ (fbm(p*2.2+3.1)-.5)*.55;
  float stain=smoothstep(.62,.40,d);
  vec3 sc=mix(vec3(.80,.70,.52),vec3(.66,.52,.34),smoothstep(.45,.1,d));
  base=mix(base,base*sc/.8,stain);
  float tide=exp(-pow((d-.60)/.012,2.))+.7*exp(-pow((d-.44)/.01,2.))+.5*exp(-pow((d-.28)/.009,2.));
  base*=1.-tide*.28;
  float wet=smoothstep(.16,.0,length(p-c));
  base*=1.-wet*.35;
  return base;
}
float ceilLight(vec2 p){ // 왼쪽 창에서 들어오는 빛
  return .25+1.1*exp(-pow((p.x+1.4)*.55,2.))*smoothstep(4.5,.5,p.y);
}
vec3 ceilingCol(vec3 ro, vec3 rd, vec2 c){
  if(rd.y<=0.) return vec3(.02,.02,.025);
  float t=(1.-ro.y)/rd.y; vec3 p=ro+rd*t;
  vec3 col=plaster(p.xz,c)*ceilLight(p.xz);
  col*=exp(-t*.16);
  return col;
}
bool ell(vec3 ro, vec3 rd, vec3 c, vec3 r, out vec3 n, out float tt){
  vec3 o=(ro-c)/r, d=rd/r;
  float a=dot(d,d), b=dot(o,d), cc=dot(o,o)-1.;
  float h=b*b-a*cc; if(h<0.) return false;
  tt=(-b-sqrt(h))/a; if(tt<0.) return false;
  vec3 q=o+d*tt; n=normalize(q/r); return true;
}
vec3 shot1(vec2 uv){
  float t=T;
  float pitch=.52;
  vec3 ro=vec3(0.,0.,0.);
  vec3 fw=normalize(vec3(0.,sin(pitch),cos(pitch)));
  vec3 up=normalize(vec3(0.,cos(pitch),-sin(pitch)));
  vec3 rt=vec3(1.,0.,0.);
  float zoom=1.7+t*.18;
  vec3 rd=normalize(uv.x*rt+uv.y*up+zoom*fw);
  vec2 hang=vec2(.0,2.05);
  vec3 col=ceilingCol(ro,rd,hang);
  // 물방울: 맺힘 → 늘어짐 → 떨어짐
  float r=mix(.035,.058,smoothstep(0.,.42,t));
  float st=1.+smoothstep(.3,.5,t)*.35;
  float td=.5;
  float yc=1.-r*st*.92;
  float fall=max(t-td,0.);
  yc-=7.*fall*fall;
  st=t>td?1.25+fall*2.:st;
  vec3 c=vec3(hang.x,yc,hang.y);
  vec3 n; float tt;
  if(ell(ro,rd,c,vec3(r,r*st,r),n,tt)){
    vec3 rr=refract(rd,n,1./1.33);
    vec3 refr=ceilingCol(c,rr,hang)*.85;
    vec3 rf=reflect(rd,n);
    vec3 refl=ceilingCol(c,rf,hang)+vec3(1.)*pow(max(dot(rf,normalize(vec3(-.8,.35,.5))),0.),30.)*2.;
    float fr=.04+.96*pow(1.-max(dot(-rd,n),0.),5.);
    vec3 dc=mix(refr,refl,fr);
    dc*=mix(.55,1.,smoothstep(.0,.5,dot(-rd,n)));
    dc+=vec3(1.)*pow(max(dot(rf,normalize(vec3(-.6,-.2,.75))),0.),120.)*3.;
    col=dc;
  }
  // 떨어지기 전 목(neck)
  if(t>.34&&t<td+.03){
    // 얇은 연결부: 화면상 근사
  }
  return col;
}
vec3 floorCol(vec2 p){
  float w=fbm(vec2(p.x*1.2,p.y*18.));
  vec3 c=mix(vec3(.20,.12,.065),vec3(.34,.21,.11),w);
  c*=.82+.18*step(.5,fract(p.x*1.8));
  return c*.5;
}
float lampRefl(vec3 rf){
  if(rf.y<=0.) return 0.;
  vec2 q=rf.xz/rf.y;
  float tube=smoothstep(.36,.32,abs(q.x-.05))*smoothstep(.022,.012,abs(q.y-.62));
  float halo=exp(-pow(abs(q.x-.05)*1.6,2.)*3.-pow((q.y-.62)*7.,2.));
  return tube*4.+halo*.18;
}
vec2 ripple(vec2 P, vec2 ic, float age){
  if(age<=0.) return vec2(0.);
  vec2 dp=P-ic; float d=length(dp)+1e-4;
  float front=.5*age;
  float env=exp(-2.2*age)*exp(-8.*abs(d-front))*smoothstep(0.,.03,front);
  float k=50.;
  float g=k*cos(k*(d-front))*env*.018;
  float env2=exp(-3.*age)*exp(-10.*abs(d-front*.62));
  g+=k*.8*cos(k*.8*(d-front*.62))*env2*.012;
  return dp/d*g;
}
vec3 shot2(vec2 uv){
  float t=T;
  vec3 ro=vec3(0.,1.6,-1.25);
  vec3 ta=vec3(0.,-.1,.12);
  vec3 fw=normalize(ta-ro), rt=normalize(cross(vec3(0,1,0),fw)), up=cross(fw,rt);
  float zoom=1.5+(t-.72)*.28;
  vec3 rd=normalize(uv.x*rt+uv.y*up+zoom*fw);
  float rimR=.80, rimW=.075, wl=-.14;
  vec2 ic=vec2(.03,.12);
  float age=t-1.0;
  vec3 col;
  float t0=-ro.y/rd.y; vec3 p0=ro+rd*t0; float r0=length(p0.xz);
  vec3 red=vec3(.80,.09,.08);
  if(r0>rimR+rimW){
    float tf=(-.32-ro.y)/rd.y; vec3 pf=ro+rd*tf;
    col=floorCol(pf.xz);
    col*=.35+.65*smoothstep(rimR+.12,rimR+.55,length(pf.xz-vec2(-.08,.06)));
  } else if(r0>rimR){
    float s=(r0-rimR)/rimW;
    float bump=sin(s*3.14159);
    col=red*(.25+.55*bump)+vec3(1.,.85,.85)*pow(bump,24.)*.45;
    col*=.7+.3*smoothstep(-.8,.8,-p0.x);
  } else {
    float tw=(wl-ro.y)/rd.y; vec3 pw=ro+rd*tw; float rw=length(pw.xz);
    float innerR=rimR-.05;
    if(rw>innerR){
      // 대야 안쪽 벽
      float depth=clamp((rw-innerR)/.18,0.,1.);
      col=red*(.18+.4*depth);
      float ang=atan(pw.z,pw.x);
      col+=vec3(.9,.5,.5)*pow(max(sin(ang+.6),0.),12.)*.12;
    } else {
      vec2 gr=ripple(pw.xz,ic,age);
      gr+=vec2(fbm3(pw.xz*6.)-.5,fbm3(pw.xz*6.+5.)-.5)*.006;
      vec3 n=normalize(vec3(-gr.x,1.,-gr.y));
      vec3 rf=reflect(rd,n);
      float fr=.02+.98*pow(1.-max(dot(-rd,n),0.),5.);
      vec3 env=vec3(.035,.03,.032)+vec3(1.,.98,.94)*lampRefl(rf);
      vec3 body=vec3(.12,.018,.015)*(.6+.4*smoothstep(innerR,0.,rw));
      col=body+env*clamp(fr+.22,0.,1.);
      col*=.75+.25*smoothstep(innerR,innerR-.2,rw);
    }
  }
  // 떨어지는 물방울 (충격 전, 세로로 늘어진 모션블러)
  if(t<1.0){
    float u=clamp((t-.72)/.28,0.,1.);
    float yy=mix(1.25,wl,u*u);
    vec3 c=vec3(ic.x,yy+.03,ic.y);
    vec3 st=vec3(1.,3.2,1.);
    vec3 o=(ro-c)/st, d=rd/st; float rr=.022;
    float A2=dot(d,d),B=dot(o,d),C=dot(o,o)-rr*rr,h=B*B-A2*C;
    if(h>0.){
      vec3 q=o+d*(-B-sqrt(h))/A2; vec3 n=normalize(q/st);
      col=vec3(.12,.12,.14)+vec3(1.)*lampRefl(reflect(rd,n))*.6+vec3(.5)*pow(1.-max(dot(-rd,n),0.),3.);
    }
  }
  // 물기둥 + 왕관 방울
  if(age>0.&&age<.5){
    float jh=.2*sin(3.14159*clamp(age/.42,0.,1.));
    vec3 c=vec3(ic.x,wl+jh*.5,ic.y);
    vec3 st=vec3(1.,2.4,1.); float rj=.02*(1.-age*1.2);
    vec3 o=(ro-c)/st, d=rd/st;
    float A2=dot(d,d),B=dot(o,d),C=dot(o,o)-rj*rj,h=B*B-A2*C;
    if(h>0.&&rj>0.){ vec3 q=o+d*(-B-sqrt(h))/A2; vec3 n=normalize(q/st);
      col=vec3(.1,.08,.09)+vec3(1.)*lampRefl(reflect(rd,n))*.5+vec3(.55)*pow(1.-max(dot(-rd,n),0.),2.); }
    for(int i=0;i<10;i++){
      float fi=float(i); float ang=fi/10.*6.2831+.3;
      vec2 dir=vec2(cos(ang),sin(ang));
      float sp=.3+.25*h11(fi);
      vec3 q=vec3(ic.x+dir.x*sp*age, wl+.5*age-2.2*age*age, ic.y+dir.y*sp*age);
      if(q.y<wl) continue;
      vec3 oq=ro-q; float bq=dot(oq,rd), cq=dot(oq,oq)-.008*.008; float hq=bq*bq-cq;
      if(hq>0.) col=vec3(.8,.82,.85);
    }
  }
  return col;
}
void main(){
  vec2 uv=UV();
  vec3 col=T<.72?shot1(uv):shot2(uv);
  col=tone(col*1.15);
  // 약간 차갑게 + 대비
  col=pow(col,vec3(1.05,1.0,.97));
  gl_FragColor=vec4(col,1.);
}`;

// ---------------------------------------------------------------- 불
FS.fire = LIB + `
void main(){
  vec2 uv=UV(); uv/=1.+.06*U;
  float y=uv.y+.5;
  float t=T+4.3;
  vec2 p=vec2(uv.x*2.4,y*1.4);
  float n1=fbm(p*1.4-vec2(0.,t*2.8));
  float n2=fbm(p*3.0+vec2(n1*1.9,-t*4.4));
  float tongues=.5+.5*sin(uv.x*9.+n1*6.);
  float f=n2*1.25-y*1.45+.18+.22*n1+.22*tongues*(1.-y);
  f=clamp(f,0.,1.);
  vec3 col=vec3(.35,.025,0.)*smoothstep(.0,.25,f);
  col+=vec3(1.7,.5,.06)*pow(f,2.2);
  col+=vec3(1.4,1.05,.55)*pow(f,5.)*2.;
  // 연기 (위쪽 어둡게)
  col*=1.-smoothstep(.2,.95,y)*.55*(1.-f);
  for(int k=0;k<28;k++){
    float fk=float(k);
    float sp=.25+.5*h11(fk+2.);
    vec2 e=vec2((h11(fk)-.5)*A*1.9+.04*sin(T*6.+fk), fract(h11(fk+1.)+T*sp)*1.25-.6);
    float d=length(uv-e);
    col+=vec3(2.,.7,.15)*exp(-d*d/(.00002+.00004*h11(fk+3.)))*1.2;
  }
  gl_FragColor=vec4(tone(col*.9),1.);
}`;

// ---------------------------------------------------------------- 물
FS.water = LIB + `
float H(vec2 P){
  float h=0.;
  for(int i=0;i<14;i++){
    float fi=float(i);
    vec2 c=vec2((h11(fi)-.5)*3.6,.9+h11(fi+9.)*1.9);
    float ts=-.9+h11(fi+4.)*1.3;
    float a=T-ts; if(a<0.) continue;
    float d=length(P-c);
    float fr=.42*a;
    h+=sin(55.*(d-fr))*exp(-2.2*a)*exp(-10.*abs(d-fr))*.012;
  }
  return h;
}
void main(){
  vec2 uv=UV(); uv/=1.+.05*U;
  float gz=1.15/(.92-uv.y);
  vec2 P=vec2(uv.x*gz,gz);
  float e=.002;
  float h0=H(P);
  vec2 gr=vec2(H(P+vec2(e,0.))-h0,H(P+vec2(0.,e))-h0)/e;
  gr+=vec2(fbm3(P*6.+T*.4)-.5,fbm3(P*6.+7.-T*.3)-.5)*.08;
  vec3 n=normalize(vec3(-gr.x,1.,-gr.y*1.3));
  vec3 rd=normalize(vec3(uv.x,-.55+uv.y*.6,1.));
  vec3 rf=reflect(rd,n);
  float win=smoothstep(.2,.35,rf.y)*smoothstep(.9,.1,abs(rf.x+.15));
  vec3 env=mix(vec3(.01,.03,.05),vec3(.55,.75,.9),win*.7);
  env+=vec3(1.)*pow(max(dot(rf,normalize(vec3(-.3,.6,1.))),0.),90.)*3.;
  float fr=.02+.98*pow(1.-max(dot(-rd,n),0.),5.);
  vec3 deep=vec3(.0,.035,.055);
  vec3 col=mix(deep,env,clamp(fr*1.6+.12,0.,1.));
  col*=smoothstep(3.6,1.,gz)*.7+.3;
  gl_FragColor=vec4(tone(col*1.3),1.);
}`;

// ---------------------------------------------------------------- 그을음 / 연기
FS.soot = LIB + `
void main(){
  vec2 uv=UV(); uv/=1.+.05*U;
  float grow=.35+.65*(1.-pow(1.-clamp(U,0.,1.),2.));
  vec2 o=vec2(0.,-.46);
  vec2 p=uv-o;
  // 흰 벽
  vec3 wall=vec3(.78,.75,.70)*(.9+.12*fbm(uv*5.))-vn(uv*150.)*.03;
  wall*=.75+.3*smoothstep(-.6,.5,uv.y);
  // V자 그을음 (콘센트에서 위로 번짐)
  float n=fbm(uv*4.+vec2(0.,-T*.2));
  float w=.05+.62*max(p.y,0.);
  float v=smoothstep(w,w*.25,abs(p.x)+(n-.5)*.22*(.3+p.y));
  v*=smoothstep(-.02,.06,p.y)*smoothstep(1.1*grow,1.1*grow-.3,p.y+(n-.5)*.2);
  float ceil=smoothstep(.28,.5,uv.y)*smoothstep(.2,.9,grow)*(.6+.4*n);
  float d=clamp(max(v*(.65+.5*n),ceil*.8),0.,1.);
  vec3 col=mix(wall,vec3(.035,.03,.028),d);
  col=mix(col,vec3(.18,.13,.09),smoothstep(.0,.5,d)*(1.-d)*.6);
  // 콘센트
  vec2 q=uv-o-vec2(0.,.02);
  float plate=step(abs(q.x),.05)*step(abs(q.y),.07);
  vec3 pc=mix(vec3(.72,.69,.63),vec3(.10,.08,.07),smoothstep(-.07,.07,q.y)*.8+.2);
  col=mix(col,pc,plate);
  float holes=step(length((q-vec2(-.018,0.))*vec2(1.,.5)),.009)+step(length((q-vec2(.018,0.))*vec2(1.,.5)),.009);
  col=mix(col,vec3(.02),clamp(holes,0.,1.)*plate);
  // 연기 안개
  float sm=fbm(uv*2.5+vec2(0.,-T*.6));
  col=mix(col,vec3(.12,.11,.10),smoothstep(.45,.85,sm)*.35);
  gl_FragColor=vec4(tone(col*1.1),1.);
}`;

// ---------------------------------------------------------------- 균열
FS.crack = LIB + `
float path(float s,float seed){return .10*s+.14*(fbm(vec2(s*1.6,seed))-.5)+.035*(fbm(vec2(s*9.,seed+4.))-.5);}
void main(){
  vec2 uv=UV(); uv/=1.+.05*U;
  bool H_=A>1.;
  float s=H_?uv.x:uv.y, b=H_?uv.y:-uv.x;
  float L=H_?A*.5+.1:.6;
  // 콘크리트
  vec2 tp=uv*5.;
  float n=fbm(tp), fine=vn(uv*140.);
  float pores=smoothstep(.82,.9,vn(uv*95.+3.))*.5;
  float hx=fbm(tp+vec2(.01,0.))-n, hy=fbm(tp+vec2(0.,.01))-n;
  vec3 N=normalize(vec3(-hx*9.,-hy*9.,1.));
  float lit=.55+.6*max(dot(N,normalize(vec3(-.5,.6,.6))),0.);
  vec3 col=vec3(.46,.45,.43)*(.8+.35*n)*lit-fine*.05-pores*.15;
  // 균열 진행
  float head=mix(-L,L,1.-pow(1.-clamp(U*1.25,0.,1.),2.2));
  float cy=path(s,1.3);
  float w=(.0035+.006*fbm(vec2(s*7.,2.)))*smoothstep(head,head-.25,s);
  float d=b-cy;
  float m=smoothstep(w+1e-5,w*.4,abs(d))*step(s,head)*step(1e-5,w);
  // 가지
  float s0=-.2*L, cy2=cy;
  float bs=s-s0;
  float by=path(s0,1.3)+bs*.55+.05*(fbm(vec2(bs*6.,7.))-.5);
  float head2=head-s0;
  float w2=.0028*smoothstep(head2,head2-.15,bs)*step(0.,bs)*smoothstep(.45,.2,bs);
  float m2=smoothstep(w2+1e-5,w2*.4,abs(b-by))*step(bs,head2)*step(1e-5,w2);
  float mm=max(m,m2);
  // 가장자리 음영 (틈의 깊이)
  float edge=smoothstep(w*3.5+1e-5,w,abs(d))*step(s,head)*step(1e-5,w);
  col*=1.-edge*.25*step(0.,d);
  col+=edge*.06*step(d,0.);
  col=mix(col,vec3(.02,.018,.016),mm);
  // 먼지
  for(int k=0;k<14;k++){
    float fk=float(k);
    float ss=mix(-L,head,h11(fk));
    vec2 pp=H_?vec2(ss,path(ss,1.3)):vec2(-path(ss,1.3),ss);
    pp.y-=fract(h11(fk+1.)+T*.8)*.25; pp.x+=(h11(fk+2.)-.5)*.03;
    col+=vec3(.9,.85,.8)*exp(-dot(uv-pp,uv-pp)/.000008)*.5*step(ss,head);
  }
  gl_FragColor=vec4(tone(col*1.05),1.);
}`;

// ---------------------------------------------------------------- 손전등 현장 조사
FS.flashlight = LIB + `
void main(){
  vec2 uv=UV(); uv/=1.+.04*U;
  // 불탄 벽 (거북등 탄화 패턴)
  vec2 v=vor(uv*vec2(9.,13.)+vec2(0.,fbm(uv*2.)*2.));
  float cells=smoothstep(.0,.07,v.y);
  float n=fbm(uv*4.);
  vec3 alb=mix(vec3(.018,.016,.015),vec3(.10,.085,.07),n)*mix(.25,1.,cells);
  alb+=vec3(.12,.11,.10)*smoothstep(.62,.8,fbm(uv*3.+5.))*.6; // 재
  float gloss=pow(cells,6.)*.25;
  // 손전등 빔
  float sx=mix(-.55,.42,eio(U*1.05))*(A>1.?A*.55:.8);
  vec2 c=vec2(sx,.04+.03*sin(T*4.));
  vec2 d=(uv-c)*vec2(1.,1.18);
  float r2=dot(d,d);
  float spot=exp(-r2/.05)*1.6+exp(-r2/.006)*1.2+exp(-r2/.25)*.12;
  vec3 light=vec3(1.,.93,.82)*spot;
  vec3 col=alb*(.05+light*2.4)+gloss*light*.4;
  // 빔 속 먼지
  for(int k=0;k<30;k++){
    float fk=float(k);
    vec2 pp=vec2((h11(fk)-.5)*A*1.2,(h11(fk+5.)-.5)*.9)+vec2(sin(T*.8+fk)*.02,T*.03*(h11(fk+2.)-.5));
    float dd=length(uv-pp);
    col+=vec3(1.,.95,.85)*exp(-dd*dd/.000012)*spot*.6;
  }
  gl_FragColor=vec4(tone(col*1.2),1.);
}`;

// ---------------------------------------------------------------- 복구: 페인트 롤러
FS.paint = LIB + `
void main(){
  vec2 uv=UV();
  bool H_=A>1.;
  float s=H_?uv.x:-uv.y, b=H_?uv.y:uv.x;
  float L=H_?A*.5:.5;
  float n=fbm(uv*3.);
  // 얼룩진 헌 벽
  vec3 old=vec3(.46,.40,.33)*(.8+.3*n);
  float d=length((uv-vec2(-.1,.15))*vec2(1.,1.2))+(fbm(uv*2.5+2.)-.5)*.5;
  old*=1.-smoothstep(.55,.3,d)*.18;
  old*=1.-exp(-pow((d-.55)/.012,2.))*.3-exp(-pow((d-.38)/.01,2.))*.2;
  old*=.9+.1*smoothstep(.75,.2,fbm(uv*9.));
  // 새 페인트
  float edge=mix(-L*.75,L*.95,1.-pow(1.-clamp(U,0.,1.),2.))+.012*(fbm(vec2(b*30.,1.))-.5);
  float fresh=smoothstep(edge+.003,edge-.003,s);
  vec3 nw=vec3(.95,.93,.885)*(.97+.03*vn(uv*vec2(260.,55.)));
  nw*=1.-.05*smoothstep(-.4,.5,uv.y);
  float sheen=exp(-pow((s-edge+.05)/.05,2.))*.12;
  vec3 col=mix(old,nw+sheen,fresh);
  // 롤러
  float rw=.075;
  float x=(s-edge)/rw;
  if(x>0.&&x<1.){
    float cyl=sin(x*3.14159);
    float nap=vn(vec2(x*40.,b*120.))*.5+vn(vec2(x*80.,b*260.+T*50.))*.5;
    vec3 rc=vec3(.93,.92,.9)*(.35+.7*cyl)*(.85+.25*nap);
    col=rc;
  }
  col*=.95+.08*uv.y;
  gl_FragColor=vec4(tone(col*1.05),1.);
}`;

// ---------------------------------------------------------------- 일상: 아침 햇살
FS.sunlight = LIB + `
void main(){
  vec2 uv=UV(); uv/=1.+.03*U;
  vec3 wall=vec3(.80,.66,.50)*(.92+.1*fbm(uv*4.));
  vec2 q=mat2(.94,-.34,.34,.94)*(uv-vec2(.05+T*.02,0.));
  float win=smoothstep(.75,.5,abs(q.x))*smoothstep(.48,.3,abs(q.y+.02));
  float blind=smoothstep(.2,.5,fract(q.y*9.+.2))*smoothstep(.98,.7,fract(q.y*9.+.2));
  float leaf=smoothstep(.45,.6,fbm(uv*3.2+vec2(T*.15,0.)+2.));
  float light=win*mix(blind,1.,.15)*(1.-leaf*.65);
  light=light*.9+win*.08;
  vec3 col=wall*(.16+vec3(1.25,.95,.62)*light*1.25);
  col+=vec3(1.,.75,.4)*exp(-length(uv-vec2(.25,.2))*1.6)*.25;
  for(int k=0;k<26;k++){
    float fk=float(k);
    vec2 pp=vec2((h11(fk)-.5)*A*1.1+sin(T*.6+fk)*.03,(h11(fk+3.)-.5)*.9+T*.02*(h11(fk+1.)-.5));
    float dd=length(uv-pp);
    float sz=.00003+.00012*h11(fk+7.);
    col+=vec3(1.,.9,.7)*exp(-dd*dd/sz)*.35;
  }
  gl_FragColor=vec4(tone(col*1.15),1.);
}`;

// ---------------------------------------------------------------- 훅 v2: 멀티탭 스파크
FS.strip = LIB + `
const vec3 RO=vec3(.82,.55,-1.62);
const vec3 TA=vec3(-.05,.08,.12);
const vec3 SP=vec3(.055,.19,-.555);   // 스파크 위치 (앞쪽 플러그와 소켓 틈)
float sdRBox(vec3 p, vec3 b, float r){vec3 q=abs(p)-b+r;return length(max(q,0.))+min(max(q.x,max(q.y,q.z)),0.)-r;}
float sdCylY(vec3 p, float r, float h){vec2 d=abs(vec2(length(p.xz),p.y))-vec2(r,h);return min(max(d.x,d.y),0.)+length(max(d,0.));}
float sdCap(vec3 p, vec3 a, vec3 b, float r){vec3 pa=p-a,ba=b-a;float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);return length(pa-ba*h)-r;}
// 재질: 1 바닥, 2 멀티탭, 3 플러그, 4 스위치, 5 전선
vec2 map(vec3 p){
  vec2 r=vec2(p.y,1.);
  float body=sdRBox(p-vec3(0.,.09,.1),vec3(.2,.09,.95),.045);
  for(int i=0;i<3;i++){
    float z=-.46+float(i)*.46;
    body=max(body,-sdCylY(p-vec3(0.,.18,z),.118,.035));   // 둥근 소켓 홈
  }
  if(body<r.x) r=vec2(body,2.);
  float sw=sdRBox(p-vec3(0.,.185,.86),vec3(.07,.02,.05),.015);
  if(sw<r.x) r=vec2(sw,4.);
  for(int i=0;i<2;i++){
    float z=i==0?-.46:.46;
    float pl=sdCylY(p-vec3(0.,.235,z),.1,.065)-.012;
    float cord=sdCap(p,vec3(0.,.3,z),vec3(i==0?-.6:.55,.03,z+.45),.022);
    if(pl<r.x) r=vec2(pl,3.);
    if(cord<r.x) r=vec2(cord,5.);
  }
  return r;
}
vec3 nrm(vec3 p){vec2 e=vec2(.0015,0.);return normalize(vec3(map(p+e.xyy).x-map(p-e.xyy).x,map(p+e.yxy).x-map(p-e.yxy).x,map(p+e.yyx).x-map(p-e.yyx).x));}
float flash(float t){
  float a=t-.625; if(a<0.) return 0.;
  float f=exp(-a*9.)*2.6+exp(-a*2.2)*.25;
  f*=.75+.25*sin(a*190.)*sin(a*77.);
  return f;
}
vec3 proj(vec3 p, vec3 ro, vec3 rt, vec3 up, vec3 fw, float zm){vec3 q=p-ro;float z=dot(q,fw);return vec3(dot(q,rt)/z*zm,dot(q,up)/z*zm,z);}
void main(){
  vec2 uv=UV();
  float t=T;
  float shake=flash(t)*.004;
  vec3 ro=RO+vec3(sin(t*97.)*shake,cos(t*83.)*shake,0.)+vec3(0.,0.,t*.05);
  vec3 ta=TA; float zm=1.85;
  if(A<1.){ ro+=vec3(.25,.18,-.25); ta=vec3(.02,.17,-.45); zm=1.35; }
  vec3 fw=normalize(ta-ro), rt=normalize(cross(vec3(0,1,0),fw)), up=cross(fw,rt);
  vec3 rd=normalize(uv.x*rt+uv.y*up+zm*fw);
  float tt=0.; vec2 h=vec2(1.,0.);
  for(int i=0;i<110;i++){h=map(ro+rd*tt); if(h.x<.0006||tt>6.) break; tt+=h.x*.9;}
  float F=flash(t);
  vec3 moon=normalize(vec3(-.6,.75,.35));
  vec3 col=vec3(.004,.005,.008);
  if(tt<6.){
    vec3 p=ro+rd*tt, n=nrm(p);
    vec3 alb; float spec=.2, rough=40.;
    if(h.y==1.){ // 나무 바닥
      float g=fbm(vec2(p.x*1.3,p.z*14.))*.6+fbm(vec2(p.x*9.,p.z*60.))*.4;
      alb=mix(vec3(.16,.09,.05),vec3(.30,.18,.10),g)*(.85+.15*step(.5,fract(p.x*1.6+.2)));
      spec=.15; rough=18.;
    } else if(h.y==2.){ alb=vec3(.86,.86,.84); spec=.35; rough=60.;
      float burn=smoothstep(.2,.0,length(p-SP))*smoothstep(.62,1.4,t);
      alb=mix(alb,vec3(.08,.06,.05),burn*.8);
      if(p.y<.16){ vec2 hp=vec2(abs(p.x)-.045,fract((p.z+.46)/.46+.5)*.46-.23); alb*=.55; alb*=mix(.15,1.,smoothstep(.012,.02,length(hp))); }
    } else if(h.y==3.){ alb=vec3(.80,.80,.78); spec=.35; rough=50.;
      float burn=smoothstep(.16,.0,length(p-SP))*smoothstep(.62,1.4,t); alb=mix(alb,vec3(.06,.05,.04),burn*.85); }
    else if(h.y==4.){ alb=vec3(.9,.25,.12); spec=.4; rough=60.; }
    else { alb=vec3(.72,.72,.70); spec=.25; rough=30.; }
    // 달빛(창)
    float dm=max(dot(n,moon),0.);
    col=alb*vec3(.34,.37,.46)*(.16+dm*.75);
    col+=alb*vec3(.55,.42,.30)*max(dot(n,normalize(vec3(.8,.35,-.5))),0.)*.10;
    col+=vec3(.35,.45,.7)*pow(max(dot(reflect(rd,n),moon),0.),rough)*spec*.5;
    // LED 빛
    vec3 lp=vec3(0.,.22,.86); vec3 ld=lp-p; float ll=length(ld);
    col+=alb*vec3(1.,.28,.12)*max(dot(n,ld/ll),0.)*.018/(ll*ll+.02);
    // 스파크 빛
    vec3 sd=SP-p; float sl=length(sd);
    float lam=max(dot(n,sd/sl),0.);
    vec3 sc=mix(vec3(1.,.72,.4),vec3(.8,.9,1.),exp(-(t-.625)*14.));
    col+=alb*sc*lam*F*.09/(sl*sl+.004);
    col+=sc*pow(max(dot(reflect(rd,n),sd/sl),0.),rough)*spec*F*.05/(sl*sl+.01);
    col*=exp(-tt*.12);
    // 스위치 LED 자체 발광
    if(h.y==4.) col+=vec3(1.,.22,.08)*.9;
  }
  // 스크린 공간: 스파크 섬광과 불티
  vec3 sp=proj(SP,ro,rt,up,fw,zm);
  float d=length(uv-sp.xy);
  col+=vec3(1.,.85,.6)*F*(exp(-d*d/.0004)*1.4+exp(-d*d/.006)*.35);
  col+=vec3(.75,.85,1.)*F*exp(-d*d/.00005)*2.;
  float a0=t-.625;
  if(a0>0.){
    for(int k=0;k<44;k++){
      float fk=float(k);
      float life=.25+.6*h11(fk+1.);
      float a=a0-h11(fk+9.)*.08; if(a<0.||a>life) continue;
      vec3 v=vec3((h11(fk)-.5)*1.6,.4+h11(fk+2.)*1.3,(h11(fk+3.)-.5)*1.4);
      vec3 p1=SP+v*a+vec3(0.,-2.4*a*a,0.);
      vec3 p0=SP+v*max(a-.028,0.)+vec3(0.,-2.4*max(a-.028,0.)*max(a-.028,0.),0.);
      vec3 q1=proj(p1,ro,rt,up,fw,zm), q0=proj(p0,ro,rt,up,fw,zm);
      vec2 pa=uv-q0.xy, ba=q1.xy-q0.xy; float hh=clamp(dot(pa,ba)/max(dot(ba,ba),1e-7),0.,1.);
      float ds=length(pa-ba*hh);
      float fade=1.-a/life;
      col+=vec3(1.,.62,.25)*exp(-ds*ds/.0000035)*fade*1.6;
    }
    // 연기
    vec2 q=uv-sp.xy;
    float rise=clamp((a0-.12)/1.4,0.,1.);
    float w=.03+q.y*.35;
    float plume=smoothstep(w,0.,abs(q.x+(fbm(vec2(q.y*6.,t*.8))-.5)*.12*q.y*3.))*smoothstep(-.01,.03,q.y)*smoothstep(.05+rise*.55,rise*.3,q.y);
    float sm=fbm(vec2(q.x*9.,q.y*7.-t*1.6))*plume*rise;
    col=mix(col,vec3(.32,.33,.36)*(.25+F*1.2)+vec3(.05),clamp(sm*1.3,0.,.7));
  }
  col=tone(col*1.2);
  gl_FragColor=vec4(col,1.);
}`;

function compile(key) {
  const sh = (type, src) => {
    const s = g.createShader(type); g.shaderSource(s, src); g.compileShader(s);
    if (!g.getShaderParameter(s, g.COMPILE_STATUS)) throw new Error(key + ': ' + g.getShaderInfoLog(s));
    return s;
  };
  const p = g.createProgram();
  g.attachShader(p, sh(g.VERTEX_SHADER, VS));
  g.attachShader(p, sh(g.FRAGMENT_SHADER, FS[key]));
  g.bindAttribLocation(p, 0, 'p');
  g.linkProgram(p);
  if (!g.getProgramParameter(p, g.LINK_STATUS)) throw new Error(key + ' link: ' + g.getProgramInfoLog(p));
  progs[key] = { p, R: g.getUniformLocation(p, 'R'), T: g.getUniformLocation(p, 'T'), U: g.getUniformLocation(p, 'U') };
}

export function initGL(canvas) {
  g = canvas.getContext('webgl', { preserveDrawingBuffer: true, antialias: false, alpha: false });
  if (!g) { console.warn('no webgl'); return; }
  buf = g.createBuffer();
  g.bindBuffer(g.ARRAY_BUFFER, buf);
  g.bufferData(g.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), g.STATIC_DRAW);
  for (const k of Object.keys(FS)) compile(k);
}

export const hasGL = (k) => !!g && k in FS;

export function drawGL(key, T, U) {
  if (!g || !progs[key]) return false;
  const pr = progs[key];
  g.viewport(0, 0, g.canvas.width, g.canvas.height);
  g.useProgram(pr.p);
  g.bindBuffer(g.ARRAY_BUFFER, buf);
  g.enableVertexAttribArray(0);
  g.vertexAttribPointer(0, 2, g.FLOAT, false, 0, 0);
  g.uniform2f(pr.R, g.canvas.width, g.canvas.height);
  g.uniform1f(pr.T, T);
  g.uniform1f(pr.U, U);
  g.drawArrays(g.TRIANGLES, 0, 3);
  return true;
}
