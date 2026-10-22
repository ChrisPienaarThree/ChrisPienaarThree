const assert=require('assert');const P=require('./_pure.js');
// homography: unit square onto a skewed quad, corners must map exactly
const q=[{x:10,y:20},{x:210,y:30},{x:200,y:310},{x:5,y:290}];const w=100,h=150;const H=P.homography(w,h,q);
const map=(x,y)=>{const d=H[6]*x+H[7]*y+1;return [(H[0]*x+H[1]*y+H[2])/d,(H[3]*x+H[4]*y+H[5])/d]};
[[0,0,q[0]],[w,0,q[1]],[w,h,q[2]],[0,h,q[3]]].forEach(([x,y,t])=>{const [X,Y]=map(x,y);assert(Math.abs(X-t.x)<1e-6&&Math.abs(Y-t.y)<1e-6,'corner '+x+','+y)});
// identity-ish
const I=P.homography(50,80,[{x:0,y:0},{x:50,y:0},{x:50,y:80},{x:0,y:80}]);assert(Math.abs(I[0]-1)<1e-9&&Math.abs(I[4]-1)<1e-9);
// numbers
assert.strictEqual(P.parseNum('R 1 234,50'),1234.5);assert.strictEqual(P.parseNum('1,234.50'),1234.5);assert.strictEqual(P.parseNum('1.234,50'),1234.5);
assert.strictEqual(P.parseNum('845.5'),845.5);assert.strictEqual(P.parseNum('1,234'),1234);assert.strictEqual(P.parseNum('45,5'),45.5);assert.strictEqual(P.parseNum(''),null);assert.strictEqual(P.parseNum('abc'),null);
// dates
assert.strictEqual(P.normDate('21/10/2026'),'2026-10-21');assert.strictEqual(P.normDate('2026/10/21'),'2026-10-21');assert.strictEqual(P.normDate('5 Oct 2026'),'2026-10-05');
assert.strictEqual(P.normDate(46316),'2026-10-21');assert.strictEqual(P.normDate('31/13/2026'),'');assert.strictEqual(P.normDate(null),'');
// names and paths
assert.strictEqual(P.slug('Engen Mpumalanga (Pty) Ltd'),'Engen-Mpumalanga-Pty-Ltd');
const r={invoiceDate:'2026-10-21',supplier:'Café Böhm',invoiceNo:'INV/00123',total:845.5,currency:'ZAR'};
assert.strictEqual(P.fileBase(r),'2026-10-21_Cafe-Bohm_INV-00123_R845.50');
const used=new Set();const p1=P.buildPath('month',r,used),p2=P.buildPath('month',r,used);
assert.strictEqual(p1,'Invoices_slip/2026-10/2026-10-21_Cafe-Bohm_INV-00123_R845.50.pdf');assert(p2.endsWith('_2.pdf'));
assert.strictEqual(P.buildPath('flat',r,new Set()).split('/').length,2);
assert.strictEqual(P.fileBase({filedOn:'2026-10-22',supplier:'',total:10,currency:'USD'}),'2026-10-22_Unknown_USD10.00');
// duplicates and reg numbers
assert.strictEqual(P.dupKey({supplier:'Engen ',invoiceNo:'A-1',total:10}),P.dupKey({supplier:'ENGEN',invoiceNo:'a1',total:'10.00'}));
assert.strictEqual(P.dupKey({supplier:'',total:5}),'');
assert.strictEqual(P.nextRegNo('RCT',2026,['RCT-2026-0007','RCT-2025-0100','junk']),'RCT-2026-0008');assert.strictEqual(P.nextRegNo('RCT',2026,[]),'RCT-2026-0001');
assert.strictEqual(P.csvCell('a,"b"'),'"a,""b"""');
console.log('ALL PURE TESTS PASSED');
