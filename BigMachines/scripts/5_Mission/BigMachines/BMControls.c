//! Client: the driver's machine controls. While PageUp / PageDown (UABMBladeUp / Down) is
//! held, the server moves the blade; on release it stops where it is.
modded class MissionGameplay
{
	protected int m_BMBladeDir;
	protected BM_Bulldozer m_BMDozer;	//!< the machine the last command went to

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);
		BMUpdateControls();
	}

	protected void BMUpdateControls()
	{
		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		BM_Bulldozer dozer;
		int dir = 0;
		if (player && player.GetCommand_Vehicle())
		{
			dozer = BM_Bulldozer.Cast(player.GetCommand_Vehicle().GetTransport());
			if (dozer && dozer.CrewMember(0) == player && !GetUIManager().GetMenu())
			{
				if (GetUApi().GetInputByName("UABMBladeUp").LocalHold())
					dir = 1;
				else if (GetUApi().GetInputByName("UABMBladeDown").LocalHold())
					dir = -1;
			}
		}

		if (dir == m_BMBladeDir && dozer == m_BMDozer)
			return;
		// Stop the old machine if we left it mid-move, then command the current one
		if (m_BMDozer && m_BMDozer != dozer && m_BMBladeDir != 0)
			GetGame().RPCSingleParam(m_BMDozer, BM_RPC.BLADE, new Param1<int>(0), true);
		if (dozer && (dir != m_BMBladeDir || dozer != m_BMDozer))
			GetGame().RPCSingleParam(dozer, BM_RPC.BLADE, new Param1<int>(dir), true);
		m_BMBladeDir = dir;
		m_BMDozer = dozer;
	}
}
