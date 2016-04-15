delete F6LGOTS from F6LGOTS
where F6LGOTS.F7_ID in (select ID from f7
where SUBSTRING(f7.f7_id_import,1,CHARINDEX('_',f7.f7_id_import)-1) not in (select id from EService_Users))

delete f7 from F7
where SUBSTRING(f7.f7_id_import,1,CHARINDEX('_',f7.f7_id_import)-1) not in (select id from EService_Users)

select distinct f6lgots.id into #tmp_ids_del
from F6LGOTS with(nolock)
inner join F7 with(nolock) on F7.ID=F6LGOTS.F7_ID
inner join F2 with(nolock) on (F2.ID=F7.F2_ID or f2.id=f7.f2_id_poluch)
where f2.eservice_users_id=17 and ( f7.datprl between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f7.datprl is null)
delete f6lgots from f6lgots where f6lgots.id in (select id from #tmp_ids_del)
drop table #tmp_ids_del

IF EXISTS (SELECT * FROM tempdb..sysobjects WHERE  name = 'delf6izm' AND type = 'U') DROP TABLE tempdb.dbo.delf6izm

select distinct F6IZM.ID into tempdb.dbo.delf6izm
from F6IZM with(nolock)
inner join f6 with(nolock) on f6.ID=F6IZM.F6_ID
inner join f2 with(nolock) on f2.ID=f6.F2_ID
left join F7 with(nolock) on f7.F6DOKUM_ID=F6IZM.ID
where f2.EService_Users_id=17 and f7.K_GSP not in(11,19)  and ( f7.datprl between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f7.datprl is null)
and f6izm.id not in (select distinct F6IZM.ID from F6IZM with(nolock)
                     inner join f6 with(nolock) on f6.ID=F6IZM.F6_ID
                     inner join f2 with(nolock) on f2.ID=f6.F2_ID
                     left join F7 with(nolock) on f7.F6DOKUM_ID=F6IZM.ID
                     where f2.EService_Users_id=17 and f7.K_GSP not in(11,19)  and ( f7.datprl not between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f7.datprl is null))

select distinct f7.id into #tmp_ids_del2 from f7 with(nolock)
inner join F2 with(nolock) on (F2.id=F7.f2_id or f2.id=f7.f2_id_poluch)
where f2.eservice_users_id=17 and ( f7.datprl between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f7.datprl is null)
delete f7 from f7 where f7.id in (select id from #tmp_ids_del2)
drop table #tmp_ids_del2

insert into tempdb.dbo.delf6izm select distinct F6IZM.ID from F6IZM with(nolock)
inner join f6 with(nolock) on f6.ID=F6IZM.F6_ID
inner join f2 with(nolock) on f2.ID=f6.F2_ID
left join F7 with(nolock) on f7.F6DOKUM_ID=F6IZM.ID
where f2.EService_Users_id=17 and f6.K_GSP not in (11,19) and f7.ID is null  and ( f6izm.dzayv between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f6izm.dzayv is null)

select distinct F_TSR.id into #tmp_ids_del3
from F_TSR with(nolock)
left join F7 with(nolock) on F7.f_tsr_id=F_tsr.ID
left join F2 with(nolock) on (F2.ID=F7.F2_ID or f2.id=f7.f2_id_poluch)
where f7.id is null or (f2.eservice_users_id=17 and ( f7.datprl between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f7.datprl is null))
delete f_tsr from f_tsr where f_tsr.id in (select id from #tmp_ids_del3)
drop table #tmp_ids_del3

select distinct F_SANCUR.id into #tmp_ids_del4
from F_SANCUR with(nolock)
left join F7 with(nolock) on F7.F_SANCUR_ID=F_SANCUR.ID
left join F2 with(nolock) on (F2.ID=F7.F2_ID or f2.id=f7.f2_id_poluch)
where f7.id is null or (f2.eservice_users_id=17 and ( f7.datprl between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f7.datprl is null))
delete f_sancur from f_sancur where f_sancur.id in (select id from #tmp_ids_del4)
drop table #tmp_ids_del4

select distinct F6SUBSID.id into #tmp_ids_del5
from F6SUBSID with(nolock)
inner join F6SUBMES with(nolock) on F6SUBMES.ID=F6SUBSID.F6SUBMES_ID
inner join tempdb.dbo.delf6izm a on a.id=F6SUBMES.F6IZM_ID
delete f6subsid from f6subsid where id in ( select id from #tmp_ids_del5)
drop table #tmp_ids_del5

select distinct F6SUBMES.id into #tmp_ids_del6
from F6SUBMES with(nolock)
inner join tempdb.dbo.delf6izm a on a.id=F6SUBMES.F6IZM_ID
delete f6submes from f6submes where id in (select id from #tmp_ids_del6)
drop table #tmp_ids_del6

select distinct f22.id into #tmp_ids_del7 from F22 with(nolock) inner join f2 with(nolock) on f2.ID=F22.F2_ID where f2.EService_Users_id=17
delete f22 from f22 where id in (select id from #tmp_ids_del7)
drop table #tmp_ids_del7

select distinct f1.id into #tmp_ids_del8 from F1 with(nolock) inner join f2 with(nolock) on f2.ID=F1.F2_ID where f2.EService_Users_id=17
delete f1 from f1 where id in (select id from #tmp_ids_del8)
drop table #tmp_ids_del8

select distinct sh.id into #tmp_ids_del9 from F_SOC_HISTORY sh with(nolock)
inner join F_SOC_REQUEST sr with(nolock) on sr.ID=sh.f_soc_request_id
inner join tempdb.dbo.delf6izm a on a.id=sr.F6IZM_ID
delete f_soc_history from f_soc_history where id in (select id from #tmp_ids_del9)
drop table #tmp_ids_del9

select distinct F_SOC_REQUEST.id into #tmp_ids_del10 from F_SOC_REQUEST with(nolock)
inner join tempdb.dbo.delf6izm a on a.id=F_SOC_REQUEST.F6IZM_ID
delete f_soc_request from f_soc_request where id in (select id from #tmp_ids_del10)
drop table #tmp_ids_del10

select distinct f2#f5s.id into #tmp_ids_del12 from f2#f5s with(nolock)
inner join f2 with(nolock) on f2.id=f2#f5s.f2_id
where f2.eservice_users_id=17
delete f2#f5s from f2#f5s where id in (select id from #tmp_ids_del12)
drop table #tmp_ids_del12

delete f6izm from f6izm where id in (select id from tempdb.dbo.delf6izm)

select distinct f6.id into #tmp_ids_del13 from F6 with(nolock)
inner join F2 with(nolock) on F2.id=f6.f2_id
left join F6IZM with(nolock) on F6IZM.F6_ID=F6.ID
left join F7 with(nolock) on f7.F6_ID=f6.ID
where f2.eservice_users_id=17 and ((F6.K_GSP not in (0,8) and F6IZM.ID is null) or (F6.K_GSP in (0,8)  and ( f6.datrz between convert(datetime,'01.01.1900',104) and convert(datetime,'31.12.2020',104) or f6.datrz is null))) and f7.ID is null
delete f6 from f6 where id in (select id from #tmp_ids_del13)
drop table #tmp_ids_del13

IF EXISTS (SELECT * FROM tempdb..sysobjects WHERE  name = 'delf6izm' AND type = 'U') DROP TABLE tempdb.dbo.delf6izm

select distinct f17.id into #tmp_ids_del14
from F17 with(nolock)
inner join f2 with(nolock) on f2.ID=F17.F2_ID
left join F6IZM on F6IZM.F17_ID=F17.ID
where f2.EService_Users_id=17 and F6IZM.ID is null
delete f17 from f17 where id in (select id from #tmp_ids_del14)
drop table #tmp_ids_del14
