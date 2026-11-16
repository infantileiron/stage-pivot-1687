/** @typedef {{channel:string,gross_cents:number,refund_cents:number,fee_cents:number,checked:number}} SettlementChannel */
/** @typedef {{id:number,code:string,day:string,venue:string,play:string,seats:number,version:number,channels:SettlementChannel[],checked_total:number,net_cents:number,channel_count:number}} Performance */
/** @typedef {{id:number,performance_id:number,base_version:number,status:'draft'|'confirmed',channels:SettlementChannel[],note:string,applied_version:number|null,stale?:boolean,result:object|null}} SplitDraft */
/** @typedef {{id:number,performance_id:number,version:number,action:string,snapshot:object,created:string}} PerformanceRevision */
/** @typedef {{id:number,name:string,row_dim:string,col_dim:string,state:string,result:object}} Pivot */
/** @typedef {{row_key:string,col_key:string,gross_cents:number,refund_cents:number,fee_cents:number,net_cents:number,seats:number,checked:number,count:number,occupancy:number|null}} PivotCell */
/** @typedef {{id:number,pivot_id:number,row_key:string,col_key:string,book_cents:number,expected_cents:number,difference_cents:number,status:string,note:string}} Review */
